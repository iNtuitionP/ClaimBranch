"""Mode-specific application copy. Never rewrite source or user-authored text."""


def personal(app):
    return bool(getattr(app.recovery, 'personal_project', False))


def recovery_copy(app, text):
    if not personal(app):
        return text
    return (text.replace('encrypted', 'local').replace('Encrypted', 'Local')
            .replace('ENCRYPTED', 'LOCAL').replace('Synthetic', 'Personal')
            .replace('synthetic', 'personal').replace('SYNTHETIC', 'PERSONAL')
            .replace('storage/encryption', 'storage')
            .replace('demo project init/open', 'project init/open'))
