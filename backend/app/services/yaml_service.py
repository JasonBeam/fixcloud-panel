from dataclasses import dataclass
from difflib import unified_diff
from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import MarkedYAMLError


KNOWN_TOP_LEVEL = {
    "port",
    "socks-port",
    "mixed-port",
    "allow-lan",
    "bind-address",
    "mode",
    "log-level",
    "ipv6",
    "external-controller",
    "secret",
    "dns",
    "proxies",
    "proxy-providers",
    "proxy-groups",
    "rules",
    "rule-providers",
    "rewrite",
    "script",
}


@dataclass(slots=True)
class RoundTripDocument:
    raw: bytes
    root: CommentedMap


class YamlService:
    def __init__(self) -> None:
        self.yaml = YAML(typ="rt")
        self.yaml.preserve_quotes = True
        self.yaml.allow_duplicate_keys = False
        self.yaml.width = 4096
        self.yaml.indent(mapping=2, sequence=4, offset=2)

    def load(self, raw: bytes) -> RoundTripDocument:
        text = raw.decode("utf-8")
        try:
            data = self.yaml.load(text)
        except MarkedYAMLError as exc:
            mark = exc.problem_mark or exc.context_mark
            location = f"第 {mark.line + 1} 行、第 {mark.column + 1} 列" if mark else "位置未知"
            reason = exc.problem or exc.context or "YAML 语法错误"
            raise ValueError(f"YAML 语法错误（{location}）：{reason}") from exc
        if not isinstance(data, CommentedMap):
            raise ValueError("配置文件顶层必须是 YAML 映射")
        return RoundTripDocument(raw=raw, root=data)

    def dump_candidate(self, document: RoundTripDocument) -> bytes:
        output = StringIO()
        self.yaml.dump(document.root, output)
        candidate = output.getvalue().encode("utf-8")
        self.load(candidate)
        return candidate

    @staticmethod
    def sha256(raw: bytes) -> str:
        import hashlib

        return hashlib.sha256(raw).hexdigest()

    def to_safe_data(self, value: Any, key: str | None = None) -> Any:
        if isinstance(value, dict):
            return {str(item_key): self.to_safe_data(item_value, str(item_key)) for item_key, item_value in value.items()}
        if isinstance(value, list):
            return [self.to_safe_data(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _round_trip_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            result = CommentedMap()
            for key, item in value.items():
                result[key] = self._round_trip_value(item)
            return result
        if isinstance(value, list):
            result = CommentedSeq()
            result.extend(self._round_trip_value(item) for item in value)
            return result
        return value

    @staticmethod
    def _resolve(container: Any, path: list[str | int]) -> Any:
        current = container
        for segment in path:
            if isinstance(current, (list, CommentedSeq)):
                current = current[int(segment)]
            elif isinstance(current, (dict, CommentedMap)):
                current = current[str(segment)]
            else:
                raise ValueError(f"无法访问路径：{path}")
        return current

    def apply_operations(
        self,
        document: RoundTripDocument,
        operations: list[dict[str, Any]],
    ) -> None:
        for operation in operations:
            action = operation.get("op")
            path = operation.get("path")
            if not isinstance(path, list) or not path:
                raise ValueError("修改路径不能为空")
            if any(isinstance(segment, str) and segment in {"__proto__", "constructor"} for segment in path):
                raise ValueError("修改路径无效")

            if action == "move":
                target = self._resolve(document.root, path)
                source_index = int(operation["fromIndex"])
                target_index = int(operation["toIndex"])
                if not (0 <= source_index < len(target) and 0 <= target_index < len(target)):
                    raise ValueError("排序位置超出范围")
                if isinstance(target, (list, CommentedSeq)):
                    item = target.pop(source_index)
                    target.insert(target_index, item)
                elif isinstance(target, (dict, CommentedMap)):
                    keys = list(target.keys())
                    item_key = keys.pop(source_index)
                    keys.insert(target_index, item_key)
                    for existing_key in reversed(keys):
                        target.move_to_end(existing_key, last=False)
                else:
                    raise ValueError("排序目标必须是列表或键值映射")
                continue

            parent = self._resolve(document.root, path[:-1]) if len(path) > 1 else document.root
            key = path[-1]
            is_sequence = isinstance(parent, (list, CommentedSeq))
            normalized_key: str | int = int(key) if is_sequence else str(key)

            if action == "delete":
                if is_sequence:
                    parent.pop(int(normalized_key))
                else:
                    parent.pop(str(normalized_key), None)
                continue

            if action == "insert":
                if not is_sequence:
                    raise ValueError("只能向列表插入项目")
                parent.insert(int(normalized_key), self._round_trip_value(operation.get("value")))
                continue

            if action != "set":
                raise ValueError(f"不支持的修改操作：{action}")
            value = operation.get("value")
            existing = None
            try:
                existing = parent[normalized_key]
            except (KeyError, IndexError):
                pass
            converted = self._round_trip_value(value)
            if is_sequence and int(normalized_key) == len(parent):
                parent.append(converted)
            else:
                parent[normalized_key] = converted

    def validate_references(self, document: RoundTripDocument) -> dict[str, list[str]]:
        root = document.root
        errors: list[str] = []
        warnings: list[str] = []

        proxies = root.get("proxies", [])
        groups = root.get("proxy-groups", [])
        providers = root.get("proxy-providers", {})
        rule_providers = root.get("rule-providers", {})

        proxy_names = [
            str(item.get("name"))
            for item in proxies
            if isinstance(item, dict) and item.get("name")
        ]
        group_names = [
            str(item.get("name"))
            for item in groups
            if isinstance(item, dict) and item.get("name")
        ]
        all_names = proxy_names + group_names
        duplicates = sorted({name for name in all_names if all_names.count(name) > 1})
        if duplicates:
            errors.append(f"代理或策略组名称重复：{', '.join(duplicates)}")

        valid_targets = set(all_names) | {
            "DIRECT",
            "REJECT",
            "REJECT-DROP",
            "PASS",
            "COMPATIBLE",
            "GLOBAL",
        }
        provider_names = set(str(name) for name in providers) if isinstance(providers, dict) else set()
        rule_provider_names = (
            set(str(name) for name in rule_providers) if isinstance(rule_providers, dict) else set()
        )

        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                continue
            group_name = str(group.get("name", "未命名策略组"))
            for provider in group.get("use", []) or []:
                if str(provider) not in provider_names:
                    errors.append(f"策略组 {group_name} 引用了不存在的 proxy-provider：{provider}")
            for target in group.get("proxies", []) or []:
                if str(target) not in valid_targets:
                    warnings.append(f"策略组 {group_name} 的目标尚未解析：{target}")

        rules = root.get("rules", [])
        for index, rule in enumerate(rules if isinstance(rules, list) else []):
            if not isinstance(rule, str):
                warnings.append(f"第 {index + 1} 条规则不是字符串")
                continue
            parts = [part.strip() for part in rule.split(",")]
            if not parts:
                continue
            if parts[0] == "RULE-SET" and len(parts) >= 2 and parts[1] not in rule_provider_names:
                errors.append(f"第 {index + 1} 条规则引用不存在的 rule-provider：{parts[1]}")
            if len(parts) >= 2:
                target = parts[-2] if parts[-1].lower() == "no-resolve" and len(parts) >= 3 else parts[-1]
                if target not in valid_targets and parts[0] not in {"AND", "OR", "NOT", "SUB-RULE"}:
                    warnings.append(f"第 {index + 1} 条规则的策略目标尚未解析：{target}")

        return {
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
        }

    def full_diff(self, before: bytes, after: bytes) -> dict[str, Any]:
        before_lines = before.decode("utf-8").splitlines()
        after_lines = after.decode("utf-8").splitlines()
        lines = list(
            unified_diff(
                before_lines,
                after_lines,
                fromfile="修改前/FixCloud.yaml",
                tofile="修改后/FixCloud.yaml",
                lineterm="",
                n=3,
            )
        )
        changed = 0
        for line in lines:
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                changed += 1
        return {
            "text": "\n".join(lines),
            "changedLines": changed,
            "formatOnly": False,
        }

    def summary(self, document: RoundTripDocument) -> dict[str, Any]:
        root = document.root
        proxies = root.get("proxies") if isinstance(root.get("proxies"), CommentedSeq) else []
        groups = root.get("proxy-groups") if isinstance(root.get("proxy-groups"), CommentedSeq) else []
        rules = root.get("rules") if isinstance(root.get("rules"), CommentedSeq) else []
        proxy_providers = (
            root.get("proxy-providers")
            if isinstance(root.get("proxy-providers"), CommentedMap)
            else {}
        )
        rule_providers = (
            root.get("rule-providers")
            if isinstance(root.get("rule-providers"), CommentedMap)
            else {}
        )

        proxy_types: dict[str, int] = {}
        for proxy in proxies:
            if isinstance(proxy, dict):
                proxy_type = str(proxy.get("type", "unknown"))
                proxy_types[proxy_type] = proxy_types.get(proxy_type, 0) + 1

        rule_types: dict[str, int] = {}
        for rule in rules:
            rule_type = str(rule).split(",", 1)[0] if isinstance(rule, str) else "unknown"
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1

        unknown = [key for key in root if key not in KNOWN_TOP_LEVEL]
        return {
            "sections": {
                "general": sum(
                    key in root
                    for key in (
                        "port",
                        "socks-port",
                        "mixed-port",
                        "allow-lan",
                        "bind-address",
                        "mode",
                        "log-level",
                        "ipv6",
                    )
                ),
                "dns": len(root.get("dns", {})) if isinstance(root.get("dns"), dict) else 0,
                "proxies": len(proxies),
                "proxyGroups": len(groups),
                "proxyProviders": len(proxy_providers),
                "rules": len(rules),
                "ruleProviders": len(rule_providers),
                "rewrite": len(root.get("rewrite", [])) if root.get("rewrite") else 0,
                "script": len(root.get("script", [])) if root.get("script") else 0,
                "other": len(unknown),
            },
            "proxyTypes": proxy_types,
            "ruleTypes": rule_types,
            "unknownTopLevel": unknown,
        }
