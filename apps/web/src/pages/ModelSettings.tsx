import React, { useCallback, useEffect, useState } from 'react';
import { checkModelConfig, getCostSummary, getModelConfig, getModelStatus } from '../api/client';
import { ModelCheckResult, ModelConfig } from '../api/types';
import { useStudioStore } from '../store/useStudioStore';

export default function ModelSettings() {
  const setError = useStudioStore((s) => s.setError);
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [cost, setCost] = useState<any>(null);
  const [check, setCheck] = useState<ModelCheckResult | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setConfig(await getModelConfig());
      setCost(await getCostSummary());
      try {
        setStatus(await getModelStatus());
      } catch {
        setStatus(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载模型配置失败');
    } finally {
      setLoading(false);
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  const runCheck = async () => {
    try {
      setCheck(await checkModelConfig());
    } catch (err) {
      setError(err instanceof Error ? err.message : '模型检查失败');
    }
  };

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Model Provider</p>
          <h1>模型设置</h1>
          <p className="muted">通过 .env 配置 DeepSeek 或其他 OpenAI-compatible provider。</p>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={load} disabled={loading}>刷新</button>
          <button className="button primary" onClick={runCheck}>检查配置</button>
        </div>
      </header>

      <div className="two-column">
        <div className="panel">
          <div className="panel-title">
            <h2>当前配置</h2>
            <span className={`badge ${config?.api_key_configured ? 'success' : 'danger'}`}>
              {config?.api_key_configured ? '已配置' : '缺少 API Key'}
            </span>
          </div>
          <div className="status-list">
            <Row label="Provider" value={config?.provider} />
            <Row label="Base URL" value={config?.base_url} />
            <Row label="Flash 模型" value={config?.flash_model} />
            <Row label="Pro 模型" value={config?.pro_model} />
            <Row label="超时" value={`${config?.timeout_seconds ?? '-'} 秒`} />
          </div>
          {!config?.api_key_configured && (
            <div className="alert alert-warning">
              在项目根目录 .env 中设置 MODEL_API_KEY，或继续使用兼容旧变量 DEEPSEEK_API_KEY。
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-title">
            <h2>调用与成本</h2>
            <span className="badge">{cost?.calls_count ?? 0} calls</span>
          </div>
          <div className="status-list">
            <Row label="累计成本" value={`$${Number(cost?.total_cost_usd || 0).toFixed(4)}`} />
            <Row label="Flash 状态" value={status?.flash?.model || '-'} />
            <Row label="Pro 状态" value={status?.pro?.model || '-'} />
          </div>
          {check && (
            <div className={`alert ${check.ok ? 'alert-success' : 'alert-error'}`}>
              {check.ok ? `配置可用：${check.provider}` : check.message}
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <h2>.env 示例</h2>
        <pre className="code-block">{`MODEL_PROVIDER=deepseek
MODEL_API_KEY=sk-your-key
MODEL_BASE_URL=https://api.deepseek.com/v1
MODEL_FLASH=deepseek-v4-flash
MODEL_PRO=deepseek-v4-pro
MODEL_TIMEOUT_SECONDS=60`}</pre>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}
