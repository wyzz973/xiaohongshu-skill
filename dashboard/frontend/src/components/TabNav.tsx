interface Tab {
  key: string
  label: string
}

interface TabNavProps {
  tabs: Tab[]
  activeTab: string
  onChange: (key: string) => void
}

export default function TabNav({ tabs, activeTab, onChange }: TabNavProps) {
  return (
    <div className="flex gap-6 border-b border-gray-100">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`pb-2.5 text-sm font-medium transition-colors cursor-pointer ${
            activeTab === tab.key
              ? 'text-[#FF2442] border-b-2 border-[#FF2442]'
              : 'text-gray-400 hover:text-gray-600'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
