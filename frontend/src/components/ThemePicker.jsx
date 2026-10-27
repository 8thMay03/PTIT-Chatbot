import React from "react";
import { Monitor, Moon, Sun } from "lucide-react";

const THEMES = [
  { key: "light", label: "Sáng", icon: Sun },
  { key: "dark", label: "Tối", icon: Moon },
  { key: "system", label: "Theo hệ thống", icon: Monitor },
];

/**
 * Bộ chọn chủ đề sáng/tối/hệ thống, dùng chung giữa app sinh viên (nút Giao diện)
 * và tab Giao diện của app admin.
 */
export default function ThemePicker({ theme, onThemeChange, className = "" }) {
  return (
    <div
      className={`theme-options ${className}`.trim()}
      role="group"
      aria-label="Chế độ giao diện"
    >
      {THEMES.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          className={`theme-option ${theme === key ? "active" : ""}`}
          aria-pressed={theme === key}
          onClick={() => onThemeChange(key)}
        >
          <Icon size={22} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
