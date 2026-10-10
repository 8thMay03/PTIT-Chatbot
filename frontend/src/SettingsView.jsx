import React from "react";
import { Cpu, Monitor, Moon, Sliders, Sun } from "lucide-react";
import ConfigView from "./ConfigView";
import ModelsView from "./ModelsView";

const TABS = [
  { key: "config", label: "Cấu hình RAG", icon: Sliders },
  { key: "models", label: "Mô hình", icon: Cpu },
  { key: "appearance", label: "Giao diện", icon: Monitor },
];

const THEMES = [
  { key: "light", label: "Sáng", icon: Sun },
  { key: "dark", label: "Tối", icon: Moon },
  { key: "system", label: "Theo hệ thống", icon: Monitor },
];

export default function SettingsView({
  activeTab = "config",
  onTabChange,
  theme,
  onThemeChange,
}) {
  return (
    <section className="settings-page" aria-labelledby="settings-title">
      <div className="settings-page-heading">
        <h1 id="settings-title">Settings</h1>
        <p>Quản lý cấu hình RAG, mô hình và giao diện tại một nơi.</p>
      </div>
      <nav className="settings-tabs" aria-label="Danh mục cài đặt">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            id={`settings-tab-${key}`}
            className={`settings-tab ${activeTab === key ? "active" : ""}`}
            aria-current={activeTab === key ? "page" : undefined}
            aria-controls={`settings-panel-${key}`}
            onClick={() => onTabChange(key)}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </nav>
      {/* Giữ các form mounted để không mất bản nháp khi đổi danh mục. */}
      <div
        className="settings-panel"
        id="settings-panel-config"
        aria-labelledby="settings-tab-config"
        hidden={activeTab !== "config"}
      >
        <ConfigView />
      </div>
      <div
        className="settings-panel"
        id="settings-panel-models"
        aria-labelledby="settings-tab-models"
        hidden={activeTab !== "models"}
      >
        <ModelsView />
      </div>
      <div
        className="settings-panel appearance-panel"
        id="settings-panel-appearance"
        aria-labelledby="settings-tab-appearance"
        hidden={activeTab !== "appearance"}
      >
        <h2>Giao diện</h2>
        <p>Chọn chế độ hiển thị phù hợp với bạn.</p>
        <div
          className="theme-options"
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
        <div className="settings-language">
          <span>Ngôn ngữ giao diện</span>
          <strong>Tiếng Việt</strong>
        </div>
      </div>
    </section>
  );
}
