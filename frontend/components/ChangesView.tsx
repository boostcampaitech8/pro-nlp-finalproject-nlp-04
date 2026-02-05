'use client'

import styles from './ChangesView.module.css'
import { Tab } from './TabBar'

interface ChangesViewProps {
    documents: Tab[]
}

export default function ChangesView({ documents }: ChangesViewProps) {
    const modifiedDocs = documents.filter(doc => doc.type === 'document' && doc.isModified)

    return (
        <div className={styles.changesView}>
            <div className={styles.header}>
                <h1 className={styles.title}>Changes</h1>
                <p className={styles.subtitle}>
                    {modifiedDocs.length} {modifiedDocs.length === 1 ? 'file' : 'files'} modified
                </p>
            </div>

            {modifiedDocs.length === 0 ? (
                <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}>✨</div>
                    <div className={styles.emptyText}>No changes yet</div>
                    <div className={styles.emptySubtext}>
                        Start editing documents to see changes here
                    </div>
                </div>
            ) : (
                <ul className={styles.fileList}>
                    {modifiedDocs.map((doc) => (
                        <li key={doc.id} className={styles.fileItem}>
                            <span className={`${styles.statusBadge} ${styles.modified}`}>
                                Modified
                            </span>
                            <span className={styles.fileName}>{doc.title}</span>
                        </li>
                    ))}
                </ul>
            )}

            <div style={{ marginTop: '40px', padding: '20px', background: '#f9f9f9', borderRadius: '8px', fontSize: '14px', color: '#666' }}>
                <strong>🚧 Coming Soon:</strong>
                <ul style={{ marginTop: '12px', paddingLeft: '20px' }}>
                    <li>Git-like diff view</li>
                    <li>Line-by-line change tracking</li>
                    <li>Commit history</li>
                    <li>Revert changes</li>
                </ul>
            </div>
        </div>
    )
}
