from typing import Callable, List


AuditHook = Callable[..., None]
_audit_hooks: List[AuditHook] = []


def register_audit_hook(hook: AuditHook) -> None:
    if hook not in _audit_hooks:
        _audit_hooks.append(hook)


def emit_audit(**kwargs) -> None:
    for hook in list(_audit_hooks):
        try:
            hook(**kwargs)
        except Exception as exc:
            print(f"[DEBUG] Audit hook failed: {exc}")
