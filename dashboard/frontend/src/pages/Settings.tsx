import { useState, useEffect, useCallback, useRef } from 'react'
import {
  User,
  Shield,
  Clock,
  Play,
  Square,
  Server,
  Info,
  Calendar,
  Save,
  Plus,
  X,
  Settings2,
  Check,
} from 'lucide-react'
import Badge from '../components/Badge'
import { useStrategy, useDaemonStatus } from '../api/hooks'
import { fetchAPI } from '../api/client'

// ---------- types ----------

interface StrategyData {
  _schema_version?: string
  _description?: string
  account: {
    nickname: string
    xhs_id: string
    user_id?: string
    track: string
    sub_track?: string
    one_liner: string
  }
  persona: {
    type: string
    call_reader?: string
    call_self?: string
    emoji_density?: string
    tone_keywords: string[]
    catchphrase?: string
    forbidden_words: string[]
    background?: string
    content_form?: string
  }
  content_strategy: Record<string, unknown>
  schedule: {
    timezone?: string
    publish_frequency: string
    publish_times: string[]
    publish_count_per_day: number
    candidate_publish_times: string[]
    [key: string]: unknown
  }
  interaction: {
    daily_comment_limit: number
    daily_like_limit: number
    daily_favorite_limit?: number
    [key: string]: unknown
  }
  safety: {
    daily_favorite_limit?: number
    [key: string]: unknown
  }
  daemon: {
    loop_interval_minutes: number
    health_check_interval_seconds: number
    context_rotate_hours: number
    [key: string]: unknown
  }
  created_at?: string
  updated_at?: string
}

// ---------- helpers ----------

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function SectionCard({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: React.ElementType
  children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center gap-2 mb-4">
        <Icon size={16} className="text-gray-500" />
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function LabelRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-sm font-medium text-gray-700 w-28 shrink-0">{label}</span>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function NumberInput({
  value,
  onChange,
  min,
  max,
  step,
  className = '',
}: {
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  className?: string
}) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      min={min}
      max={max}
      step={step}
      className={`w-28 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none transition ${className}`}
    />
  )
}

function TextInput({
  value,
  onChange,
  className = '',
  placeholder = '',
}: {
  value: string
  onChange: (v: string) => void
  className?: string
  placeholder?: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none transition ${className}`}
    />
  )
}

function SliderRow({
  label,
  value,
  onChange,
  min,
  max,
  colorClass,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  colorClass: string
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-lg font-bold ${colorClass}`}>{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-red-500"
      />
      <div className="flex justify-between text-xs text-gray-300">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}

function TimeChips({
  times,
  onRemove,
  onAdd,
  accent = false,
}: {
  times: string[]
  onRemove: (index: number) => void
  onAdd: (time: string) => void
  accent?: boolean
}) {
  const [adding, setAdding] = useState(false)
  const [newTime, setNewTime] = useState('12:00')

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {times.map((t, i) => (
        <span
          key={`${t}-${i}`}
          className={`group inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium transition ${
            accent
              ? 'bg-red-50 text-red-600'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          <Clock size={12} />
          {t}
          <button
            onClick={() => onRemove(i)}
            className="ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity text-current hover:text-red-700"
          >
            <X size={12} />
          </button>
        </span>
      ))}
      {adding ? (
        <span className="inline-flex items-center gap-1.5">
          <input
            type="time"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
            className="border border-gray-200 rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none"
          />
          <button
            onClick={() => {
              if (newTime) {
                onAdd(newTime)
                setAdding(false)
                setNewTime('12:00')
              }
            }}
            className="text-red-500 hover:text-red-600"
          >
            <Check size={16} />
          </button>
          <button
            onClick={() => setAdding(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={16} />
          </button>
        </span>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-dashed border-gray-300 text-sm text-gray-400 hover:text-red-500 hover:border-red-400 transition"
        >
          <Plus size={12} />
          添加
        </button>
      )}
    </div>
  )
}

function TagChips({
  tags,
  onRemove,
  onAdd,
}: {
  tags: string[]
  onRemove: (index: number) => void
  onAdd: (tag: string) => void
}) {
  const [adding, setAdding] = useState(false)
  const [newTag, setNewTag] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (adding && inputRef.current) {
      inputRef.current.focus()
    }
  }, [adding])

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {tags.map((t, i) => (
        <span
          key={`${t}-${i}`}
          className="group inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-red-50 text-red-600 text-sm font-medium transition"
        >
          {t}
          <button
            onClick={() => onRemove(i)}
            className="ml-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-700"
          >
            <X size={12} />
          </button>
        </span>
      ))}
      {adding ? (
        <span className="inline-flex items-center gap-1.5">
          <input
            ref={inputRef}
            type="text"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && newTag.trim()) {
                onAdd(newTag.trim())
                setNewTag('')
                setAdding(false)
              } else if (e.key === 'Escape') {
                setAdding(false)
              }
            }}
            placeholder="输入后回车"
            className="border border-gray-200 rounded-lg px-2 py-1 text-sm w-28 focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none"
          />
          <button
            onClick={() => {
              if (newTag.trim()) {
                onAdd(newTag.trim())
                setNewTag('')
                setAdding(false)
              }
            }}
            className="text-red-500 hover:text-red-600"
          >
            <Check size={16} />
          </button>
          <button
            onClick={() => setAdding(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={16} />
          </button>
        </span>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full border border-dashed border-gray-300 text-sm text-gray-400 hover:text-red-500 hover:border-red-400 transition"
        >
          <Plus size={12} />
          添加
        </button>
      )}
    </div>
  )
}

// ---------- form state ----------

interface FormState {
  // daemon
  contextRotateHours: number
  healthCheckIntervalSeconds: number
  loopIntervalMinutes: number
  // schedule
  publishFrequency: string
  publishCountPerDay: number
  publishTimes: string[]
  candidatePublishTimes: string[]
  // safety
  commentLimit: number
  likeLimit: number
  favoriteLimit: number
  publishLimit: number
  // content strategy
  track: string
  oneLiner: string
  personaType: string
  toneKeywords: string[]
  forbiddenWords: string[]
}

function buildFormState(s: StrategyData): FormState {
  return {
    contextRotateHours: s.daemon.context_rotate_hours ?? 2,
    healthCheckIntervalSeconds: s.daemon.health_check_interval_seconds ?? 60,
    loopIntervalMinutes: s.daemon.loop_interval_minutes ?? 45,
    publishFrequency: s.schedule.publish_frequency ?? 'daily_single',
    publishCountPerDay: s.schedule.publish_count_per_day ?? 1,
    publishTimes: [...(s.schedule.publish_times ?? [])],
    candidatePublishTimes: [...(s.schedule.candidate_publish_times ?? [])],
    commentLimit: s.interaction?.daily_comment_limit ?? 100,
    likeLimit: s.interaction?.daily_like_limit ?? 50,
    favoriteLimit: s.interaction?.daily_favorite_limit ?? s.safety?.daily_favorite_limit ?? 50,
    publishLimit: s.schedule.publish_count_per_day ?? 4,
    track: s.account.track ?? '',
    oneLiner: s.account.one_liner ?? '',
    personaType: s.persona.type ?? '',
    toneKeywords: [...(s.persona.tone_keywords ?? [])],
    forbiddenWords: [...(s.persona.forbidden_words ?? [])],
  }
}

function formStateEqual(a: FormState, b: FormState): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

// ---------- component ----------

export default function Settings() {
  const { data: strategyRaw, isLoading: stratLoading, mutate: mutateStrategy } = useStrategy()
  const { data: daemonRaw, isLoading: daemonLoading, mutate: mutateDaemon } = useDaemonStatus()

  const [daemonAction, setDaemonAction] = useState<'starting' | 'stopping' | null>(null)
  const [form, setForm] = useState<FormState | null>(null)
  const [originalForm, setOriginalForm] = useState<FormState | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState<'success' | 'error' | null>(null)

  const strategy = (strategyRaw ?? null) as StrategyData | null
  const daemon = (daemonRaw ?? {}) as Record<string, unknown>
  const daemonState = (daemon.state ?? {}) as Record<string, unknown>
  const isRunning = Boolean(daemon.running)

  // Initialize form from strategy
  useEffect(() => {
    if (strategy && !form) {
      const initial = buildFormState(strategy)
      setForm(initial)
      setOriginalForm(initial)
    }
  }, [strategy, form])

  const hasChanges = form && originalForm ? !formStateEqual(form, originalForm) : false

  const updateForm = useCallback((patch: Partial<FormState>) => {
    setForm((prev) => (prev ? { ...prev, ...patch } : prev))
  }, [])

  // Build full strategy object for save
  function buildUpdatedStrategy(): StrategyData | null {
    if (!strategy || !form) return null
    const updated = JSON.parse(JSON.stringify(strategy)) as StrategyData
    // daemon
    updated.daemon.context_rotate_hours = form.contextRotateHours
    updated.daemon.health_check_interval_seconds = form.healthCheckIntervalSeconds
    updated.daemon.loop_interval_minutes = form.loopIntervalMinutes
    // schedule
    updated.schedule.publish_frequency = form.publishFrequency
    updated.schedule.publish_count_per_day = form.publishCountPerDay
    updated.schedule.publish_times = form.publishTimes
    updated.schedule.candidate_publish_times = form.candidatePublishTimes
    // interaction / safety limits
    if (updated.interaction) {
      updated.interaction.daily_comment_limit = form.commentLimit
      updated.interaction.daily_like_limit = form.likeLimit
      updated.interaction.daily_favorite_limit = form.favoriteLimit
    }
    // account
    updated.account.track = form.track
    updated.account.one_liner = form.oneLiner
    // persona
    updated.persona.type = form.personaType
    updated.persona.tone_keywords = form.toneKeywords
    updated.persona.forbidden_words = form.forbiddenWords
    // timestamp
    updated.updated_at = new Date().toISOString()
    return updated
  }

  async function handleSave() {
    const updated = buildUpdatedStrategy()
    if (!updated) return
    setSaving(true)
    setSaveResult(null)
    try {
      await fetchAPI('/strategy', { method: 'POST', body: JSON.stringify(updated) })
      setSaveResult('success')
      const newForm = buildFormState(updated)
      setOriginalForm(newForm)
      setForm(newForm)
      mutateStrategy()
      setTimeout(() => setSaveResult(null), 2000)
    } catch {
      setSaveResult('error')
      setTimeout(() => setSaveResult(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  async function handleDaemonStart() {
    setDaemonAction('starting')
    try {
      await fetchAPI('/daemon/start', { method: 'POST' })
      setTimeout(() => {
        mutateDaemon()
        setDaemonAction(null)
      }, 3000)
    } catch {
      setDaemonAction(null)
    }
  }

  async function handleDaemonStop() {
    setDaemonAction('stopping')
    try {
      await fetchAPI('/daemon/stop', { method: 'POST' })
      setTimeout(() => {
        mutateDaemon()
        setDaemonAction(null)
      }, 2000)
    } catch {
      setDaemonAction(null)
    }
  }

  const account = strategy?.account ?? { nickname: '', xhs_id: '', track: '', one_liner: '' }

  return (
    <div className="p-6 max-w-7xl mx-auto pb-24">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">设置</h1>
        <p className="text-sm text-gray-400 mt-0.5">账号、守护进程与运营策略配置</p>
      </div>

      <div className="space-y-6">
        {/* Section 1: Account (read-only) */}
        <SectionCard title="账号管理" icon={User}>
          {stratLoading ? (
            <Skeleton className="h-16" />
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center">
                  <User size={22} className="text-[#FF2442]" />
                </div>
                <div>
                  <p className="text-base font-semibold text-gray-800">
                    {account.nickname || '--'}
                  </p>
                  <p className="text-sm text-gray-400">
                    XHS ID: {account.xhs_id || '--'} / {account.track || '--'}
                  </p>
                </div>
              </div>
              <button
                disabled
                className="text-sm px-4 py-2 rounded-lg bg-gray-100 text-gray-400 cursor-not-allowed"
                title="多账号功能开发中"
              >
                切换账号
              </button>
            </div>
          )}
        </SectionCard>

        {/* Section 2: Daemon */}
        <SectionCard title="守护进程" icon={Server}>
          {daemonLoading ? (
            <Skeleton className="h-24" />
          ) : (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      isRunning ? 'bg-green-500 animate-pulse' : 'bg-red-400'
                    }`}
                  />
                  <Badge
                    label={isRunning ? 'Running' : 'Stopped'}
                    color={isRunning ? 'green' : 'red'}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleDaemonStart}
                    disabled={isRunning || daemonAction !== null}
                    className={`inline-flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg transition-colors duration-200 cursor-pointer ${
                      isRunning || daemonAction !== null
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : 'bg-green-500 text-white hover:bg-green-600'
                    }`}
                  >
                    <Play size={14} />
                    {daemonAction === 'starting' ? '启动中...' : '启动'}
                  </button>
                  <button
                    onClick={handleDaemonStop}
                    disabled={!isRunning || daemonAction !== null}
                    className={`inline-flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg transition-colors duration-200 cursor-pointer ${
                      !isRunning || daemonAction !== null
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : 'bg-red-500 text-white hover:bg-red-600'
                    }`}
                  >
                    <Square size={14} />
                    {daemonAction === 'stopping' ? '停止中...' : '停止'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4 text-sm mb-5">
                <div>
                  <p className="text-gray-400 mb-0.5">PID</p>
                  <p className="text-gray-700 font-mono">
                    {daemon.pid != null ? String(daemon.pid) : '--'}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 mb-0.5">Session</p>
                  <p className="text-gray-700 font-mono text-xs">
                    {daemonState.current_session
                      ? String(daemonState.current_session)
                      : '--'}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 mb-0.5">Uptime</p>
                  <p className="text-gray-700">
                    {daemonState.started_at
                      ? String(daemonState.started_at).slice(0, 19)
                      : '--'}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 mb-0.5">重建次数</p>
                  <p className="text-gray-700">
                    {daemonState.rebuild_count != null
                      ? String(daemonState.rebuild_count)
                      : '0'}
                  </p>
                </div>
              </div>

              {/* Daemon config editing */}
              {form && (
                <div className="border-t border-gray-100 pt-4 space-y-3">
                  <p className="text-xs text-gray-400 mb-2">进程配置</p>
                  <LabelRow label="轮转间隔 (h)">
                    <NumberInput
                      value={form.contextRotateHours}
                      onChange={(v) => updateForm({ contextRotateHours: v })}
                      min={1}
                      max={24}
                      step={1}
                    />
                  </LabelRow>
                  <LabelRow label="健康检查 (s)">
                    <NumberInput
                      value={form.healthCheckIntervalSeconds}
                      onChange={(v) => updateForm({ healthCheckIntervalSeconds: v })}
                      min={10}
                      max={600}
                      step={10}
                    />
                  </LabelRow>
                  <LabelRow label="循环间隔 (min)">
                    <NumberInput
                      value={form.loopIntervalMinutes}
                      onChange={(v) => updateForm({ loopIntervalMinutes: v })}
                      min={5}
                      max={120}
                      step={5}
                    />
                  </LabelRow>
                </div>
              )}
            </div>
          )}
        </SectionCard>

        {/* Section 3: Publish Schedule (editable) */}
        <SectionCard title="发布策略" icon={Calendar}>
          {stratLoading || !form ? (
            <Skeleton className="h-32" />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-8">
                <div>
                  <p className="text-xs text-gray-400 mb-1">发布频率</p>
                  <select
                    value={form.publishFrequency}
                    onChange={(e) => updateForm({ publishFrequency: e.target.value })}
                    className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:ring-2 focus:ring-red-200 focus:border-red-400 outline-none transition cursor-pointer"
                  >
                    <option value="daily_single">daily_single</option>
                    <option value="daily_double">daily_double</option>
                    <option value="every_other_day">every_other_day</option>
                  </select>
                </div>
                <div>
                  <p className="text-xs text-gray-400 mb-1">每日发布数</p>
                  <NumberInput
                    value={form.publishCountPerDay}
                    onChange={(v) => updateForm({ publishCountPerDay: v })}
                    min={1}
                    max={4}
                    step={1}
                  />
                </div>
              </div>

              <div>
                <p className="text-xs text-gray-400 mb-2">发布时间</p>
                <TimeChips
                  times={form.publishTimes}
                  accent
                  onRemove={(i) => {
                    const next = [...form.publishTimes]
                    next.splice(i, 1)
                    updateForm({ publishTimes: next })
                  }}
                  onAdd={(t) => updateForm({ publishTimes: [...form.publishTimes, t] })}
                />
              </div>

              <div>
                <p className="text-xs text-gray-400 mb-2">候选时间</p>
                <TimeChips
                  times={form.candidatePublishTimes}
                  onRemove={(i) => {
                    const next = [...form.candidatePublishTimes]
                    next.splice(i, 1)
                    updateForm({ candidatePublishTimes: next })
                  }}
                  onAdd={(t) =>
                    updateForm({ candidatePublishTimes: [...form.candidatePublishTimes, t] })
                  }
                />
              </div>
            </div>
          )}
        </SectionCard>

        {/* Section 4: Safety Limits (sliders) */}
        <SectionCard title="安全限额" icon={Shield}>
          {stratLoading || !form ? (
            <Skeleton className="h-24" />
          ) : (
            <div className="grid grid-cols-2 gap-6">
              <SliderRow
                label="评论上限"
                value={form.commentLimit}
                onChange={(v) => updateForm({ commentLimit: v })}
                min={0}
                max={200}
                colorClass="text-blue-600"
              />
              <SliderRow
                label="点赞上限"
                value={form.likeLimit}
                onChange={(v) => updateForm({ likeLimit: v })}
                min={0}
                max={100}
                colorClass="text-amber-600"
              />
              <SliderRow
                label="收藏上限"
                value={form.favoriteLimit}
                onChange={(v) => updateForm({ favoriteLimit: v })}
                min={0}
                max={100}
                colorClass="text-purple-600"
              />
              <SliderRow
                label="发布上限"
                value={form.publishLimit}
                onChange={(v) => updateForm({ publishLimit: v })}
                min={0}
                max={10}
                colorClass="text-green-600"
              />
            </div>
          )}
        </SectionCard>

        {/* Section 5: Content Strategy (NEW) */}
        <SectionCard title="内容策略" icon={Settings2}>
          {stratLoading || !form ? (
            <Skeleton className="h-32" />
          ) : (
            <div className="space-y-4">
              <LabelRow label="赛道">
                <TextInput
                  value={form.track}
                  onChange={(v) => updateForm({ track: v })}
                  className="w-full"
                />
              </LabelRow>
              <LabelRow label="定位">
                <TextInput
                  value={form.oneLiner}
                  onChange={(v) => updateForm({ oneLiner: v })}
                  className="w-full"
                />
              </LabelRow>
              <LabelRow label="人设类型">
                <TextInput
                  value={form.personaType}
                  onChange={(v) => updateForm({ personaType: v })}
                  className="w-64"
                />
              </LabelRow>
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">语气关键词</p>
                <TagChips
                  tags={form.toneKeywords}
                  onRemove={(i) => {
                    const next = [...form.toneKeywords]
                    next.splice(i, 1)
                    updateForm({ toneKeywords: next })
                  }}
                  onAdd={(t) => updateForm({ toneKeywords: [...form.toneKeywords, t] })}
                />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">禁用词</p>
                <TagChips
                  tags={form.forbiddenWords}
                  onRemove={(i) => {
                    const next = [...form.forbiddenWords]
                    next.splice(i, 1)
                    updateForm({ forbiddenWords: next })
                  }}
                  onAdd={(t) => updateForm({ forbiddenWords: [...form.forbiddenWords, t] })}
                />
              </div>
            </div>
          )}
        </SectionCard>

        {/* Section 6: About (read-only) */}
        <SectionCard title="关于" icon={Info}>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Dashboard 版本</span>
              <span className="text-gray-700 font-mono">v1.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">CLI 版本</span>
              <span className="text-gray-700 font-mono">v2.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">Workspace</span>
              <span className="text-gray-700 font-mono text-xs">~/xhs-workspace</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-500">策略文件</span>
              <span className="text-gray-700 font-mono text-xs">strategy.json</span>
            </div>
          </div>
          <p className="text-xs text-gray-300 mt-4">
            XHS 24/7 Autonomous Operations Dashboard
          </p>
        </SectionCard>
      </div>

      {/* Floating save button */}
      <div
        className={`fixed bottom-6 right-6 transition-all duration-300 ${
          hasChanges || saveResult
            ? 'translate-y-0 opacity-100'
            : 'translate-y-4 opacity-0 pointer-events-none'
        }`}
      >
        <button
          onClick={handleSave}
          disabled={saving || saveResult === 'success'}
          className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl text-white font-medium shadow-lg transition-all duration-200 cursor-pointer ${
            saveResult === 'success'
              ? 'bg-green-500'
              : saveResult === 'error'
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-[#FF2442] hover:bg-[#E0203A]'
          } ${saving ? 'opacity-70' : ''}`}
        >
          {saveResult === 'success' ? (
            <>
              <Check size={18} />
              已保存
            </>
          ) : saveResult === 'error' ? (
            <>
              <X size={18} />
              保存失败
            </>
          ) : (
            <>
              <Save size={18} />
              {saving ? '保存中...' : '保存设置'}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
