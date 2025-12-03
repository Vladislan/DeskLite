import React from 'react';

type Theme = 'light' | 'dark';

function getInitialTheme(): Theme {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark';
}

export default function ThemeToggle() {
    const [theme, setTheme] = React.useState<Theme>(() => {
        const t = getInitialTheme();
        document.documentElement.setAttribute('data-theme', t);
        return t;
    });

    const toggle = () => {
        const next: Theme = theme === 'light' ? 'dark' : 'light';
        setTheme(next);
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    };

    const label = theme === 'light' ? 'Денний' : 'Нічний';

    return (
        <button className="btn sm white" onClick={toggle} title="Змінити тему">
            {label}
        </button>
    );
}
