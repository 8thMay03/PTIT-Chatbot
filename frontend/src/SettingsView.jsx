import React from 'react';
import ConfigView from './ConfigView';
import ModelsView from './ModelsView';

export default function SettingsView({ activeTab = 'config' }) {
  return activeTab === 'models' ? <ModelsView /> : <ConfigView />;
}
