'use client'

import { useState } from 'react';
import styles from './SidebarRight.module.css';

export interface RequestMessage {
    id: number;
    role: 'user' | 'ai';
    content: string;
}

interface SidebarRightProps {
    messages: RequestMessage[];
    input: string;
    onInputChange: (value: string) => void;
    onSendMessage: (e: React.FormEvent) => void;
}

export default function SidebarRight({ messages, input, onInputChange, onSendMessage }: SidebarRightProps) {
    return (
        <aside className={styles.sidebar}>
            <div className={styles.header}>
                <h2>Assistant</h2>
            </div>
            <div className={styles.chatContainer}>
                {messages.map((msg) => (
                    <div key={msg.id} className={`${styles.message} ${styles[msg.role]}`}>
                        <div className={styles.bubble}>{msg.content}</div>
                    </div>
                ))}
            </div>
            <form onSubmit={onSendMessage} className={styles.inputForm}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => onInputChange(e.target.value)}
                    placeholder="AI에게 질문하기..."
                    className={styles.input}
                />
            </form>
        </aside>
    );
}
