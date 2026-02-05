'use client'

import styles from './TabBar.module.css'

export interface Tab {
    id: string
    title: string
    type: 'document' | 'changes'
    content?: string
    isModified?: boolean
}

interface TabBarProps {
    tabs: Tab[]
    activeTabId: string
    onTabChange: (tabId: string) => void
    onTabClose: (tabId: string) => void
    onNewTab: () => void
}

export default function TabBar({ tabs, activeTabId, onTabChange, onTabClose, onNewTab }: TabBarProps) {
    return (
        <div className={styles.tabBar}>
            {tabs.map((tab) => (
                <div
                    key={tab.id}
                    className={`${styles.tab} ${tab.id === activeTabId ? styles.active : ''} ${tab.type === 'changes' ? styles.changesTab : ''}`}
                    onClick={() => onTabChange(tab.id)}
                >
                    <span className={styles.tabTitle}>
                        {tab.type === 'changes' && '📊 '}
                        {tab.title}
                    </span>
                    {tab.isModified && <span className={styles.modified}>●</span>}
                    {tab.type !== 'changes' && (
                        <button
                            className={styles.closeButton}
                            onClick={(e) => {
                                e.stopPropagation()
                                onTabClose(tab.id)
                            }}
                            title="Close tab"
                        >
                            ×
                        </button>
                    )}
                </div>
            ))}
            <button
                className={styles.newTabButton}
                onClick={onNewTab}
                title="New document"
            >
                +
            </button>
        </div>
    )
}
