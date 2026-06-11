import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getNotificationSettings, saveNotificationSettings, testNotificationSettings } from '../api/client'
import type { NotificationSettings } from '../types/api'

const DEFAULT_SETTINGS: NotificationSettings = {
  barkEnabled: false,
  barkServerUrl: '',
  barkDeviceKey: '',
}

export default function SettingsPage() {
  const nav = useNavigate()
  const [settings, setSettings] = useState<NotificationSettings>(DEFAULT_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getNotificationSettings()
      .then(setSettings)
      .catch((e) => setError(e instanceof Error ? e.message : '读取配置失败'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const saved = await saveNotificationSettings(settings)
      setSettings(saved)
      setMessage('配置已保存')
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存配置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setMessage('')
    setError('')
    try {
      const res = await testNotificationSettings()
      setMessage(res.message || '测试推送已发送')
    } catch (e) {
      setError(e instanceof Error ? e.message : '测试推送失败')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="page settings-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav('/')}>← 返回搜索</button>
      </div>

      <div className="card">
        <h2>系统配置</h2>
        <p className="dim">第一版只保存 Bark 配置并发送测试推送，不自动触发行情或资讯提醒。</p>
      </div>

      <div className="card settings-card">
        <h3>Bark 推送</h3>
        {loading ? (
          <p className="hint">加载配置中...</p>
        ) : (
          <>
            <label className="settings-check">
              <input
                type="checkbox"
                checked={settings.barkEnabled}
                onChange={(e) => setSettings(prev => ({ ...prev, barkEnabled: e.target.checked }))}
              />
              启用 Bark 推送
            </label>

            <label className="settings-field">
              <span>Bark 服务地址</span>
              <input
                className="settings-input"
                placeholder="https://api.day.app"
                value={settings.barkServerUrl}
                onChange={(e) => setSettings(prev => ({ ...prev, barkServerUrl: e.target.value }))}
              />
            </label>

            <label className="settings-field">
              <span>Device Key</span>
              <input
                className="settings-input"
                placeholder="填写 Bark App 中显示的 Key"
                value={settings.barkDeviceKey}
                onChange={(e) => setSettings(prev => ({ ...prev, barkDeviceKey: e.target.value }))}
              />
            </label>

            <div className="settings-actions">
              <button className="collect-btn settings-btn" onClick={handleSave} disabled={saving || testing}>
                {saving ? '保存中...' : '保存配置'}
              </button>
              <button className="back-btn" onClick={handleTest} disabled={saving || testing}>
                {testing ? '发送中...' : '发送测试推送'}
              </button>
            </div>

            {message && <p className="settings-message success">{message}</p>}
            {error && <p className="settings-message error">{error}</p>}
          </>
        )}
      </div>
    </div>
  )
}
