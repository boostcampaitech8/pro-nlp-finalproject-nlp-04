'use client'

import { useState, useEffect } from 'react'
import styles from './AIModal.module.css'

type ContentType = 'image' | 'table' | 'diagram' | 'search'

interface AIModalProps {
    isOpen: boolean
    onClose: () => void
    onInsert: (content: any, type: ContentType) => void
    contextType?: ContentType | null
}

// Mock recommended images
const MOCK_IMAGES = [
    { id: 1, url: 'https://images.unsplash.com/photo-1634942537034-2531766767d1?w=400', prompt: 'Professional office workspace' },
    { id: 2, url: 'https://images.unsplash.com/photo-1618005198919-d3d4b5a92ead?w=400', prompt: 'Modern UI design interface' },
    { id: 3, url: 'https://images.unsplash.com/photo-1558655146-9f40138edfeb?w=400', prompt: 'Team collaboration meeting' },
    { id: 4, url: 'https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=400', prompt: 'Business analytics dashboard' },
    { id: 5, url: 'https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=400', prompt: 'Creative brainstorming session' },
    { id: 6, url: 'https://images.unsplash.com/photo-1553877522-43269d4ea984?w=400', prompt: 'Digital transformation concept' },
]

export default function AIModal({ isOpen, onClose, onInsert, contextType }: AIModalProps) {
    const [activeTab, setActiveTab] = useState<ContentType>(contextType || 'image')
    const [prompt, setPrompt] = useState('')

    useEffect(() => {
        if (contextType) {
            setActiveTab(contextType)
        }
    }, [contextType])

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose()
            }
        }

        if (isOpen) {
            document.addEventListener('keydown', handleEscape)
            return () => document.removeEventListener('keydown', handleEscape)
        }
    }, [isOpen, onClose])

    if (!isOpen) return null

    const handleGenerate = () => {
        if (!prompt.trim()) return

        // Mock generation based on tab
        if (activeTab === 'image') {
            onInsert({ url: 'https://via.placeholder.com/600x400?text=Generated+Image', alt: prompt }, 'image')
        } else if (activeTab === 'table') {
            onInsert({ rows: 3, cols: 3 }, 'table')
        } else if (activeTab === 'diagram') {
            onInsert({ code: `graph TD\n    A[${prompt}] --> B[Result]` }, 'diagram')
        }

        setPrompt('')
        onClose()
    }

    const handleImageClick = (image: typeof MOCK_IMAGES[0]) => {
        onInsert({ url: image.url, alt: image.prompt }, 'image')
        onClose()
    }

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                <div className={styles.header}>
                    <h2 className={styles.title}>AI Content Generator</h2>
                    <button className={styles.closeButton} onClick={onClose}>×</button>
                </div>

                <div className={styles.tabs}>
                    <button
                        className={`${styles.tab} ${activeTab === 'image' ? styles.active : ''}`}
                        onClick={() => setActiveTab('image')}
                    >
                        🎨 이미지 생성
                    </button>
                    <button
                        className={`${styles.tab} ${activeTab === 'table' ? styles.active : ''}`}
                        onClick={() => setActiveTab('table')}
                    >
                        📊 표 생성
                    </button>
                    <button
                        className={`${styles.tab} ${activeTab === 'diagram' ? styles.active : ''}`}
                        onClick={() => setActiveTab('diagram')}
                    >
                        📐 다이어그램
                    </button>
                    <button
                        className={`${styles.tab} ${activeTab === 'search' ? styles.active : ''}`}
                        onClick={() => setActiveTab('search')}
                    >
                        🔍 이미지 검색
                    </button>
                </div>

                <div className={styles.content}>
                    {activeTab === 'image' && (
                        <>
                            <h3 style={{ marginBottom: '16px', fontSize: '14px', fontWeight: '600', color: '#666' }}>
                                추천 이미지
                            </h3>
                            <div className={styles.grid}>
                                {MOCK_IMAGES.map((image) => (
                                    <div
                                        key={image.id}
                                        className={styles.imageCard}
                                        onClick={() => handleImageClick(image)}
                                    >
                                        <img src={image.url} alt={image.prompt} />
                                        <div className={styles.imagePrompt}>{image.prompt}</div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    {activeTab === 'table' && (
                        <div className={styles.emptyState}>
                            <div className={styles.emptyIcon}>📊</div>
                            <div className={styles.emptyText}>아래 프롬프트를 입력하여 표를 생성하세요</div>
                            <div style={{ fontSize: '14px', color: '#bbb', marginTop: '8px' }}>
                                예: "3행 4열 프로젝트 일정표"
                            </div>
                        </div>
                    )}

                    {activeTab === 'diagram' && (
                        <div className={styles.emptyState}>
                            <div className={styles.emptyIcon}>📐</div>
                            <div className={styles.emptyText}>다이어그램 생성 기능</div>
                            <div style={{ fontSize: '14px', color: '#bbb', marginTop: '8px' }}>
                                플로우차트, 시퀀스 다이어그램 등을 생성할 수 있습니다
                            </div>
                        </div>
                    )}

                    {activeTab === 'search' && (
                        <div className={styles.emptyState}>
                            <div className={styles.emptyIcon}>🔍</div>
                            <div className={styles.emptyText}>이미지 검색 기능</div>
                            <div style={{ fontSize: '14px', color: '#bbb', marginTop: '8px' }}>
                                곧 제공될 예정입니다
                            </div>
                        </div>
                    )}
                </div>

                <div className={styles.footer}>
                    <input
                        type="text"
                        className={styles.promptInput}
                        placeholder="프롬프트를 입력하세요..."
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                    />
                    <button className={styles.generateButton} onClick={handleGenerate}>
                        생성
                    </button>
                </div>
            </div>
        </div>
    )
}
