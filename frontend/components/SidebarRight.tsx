import { useState } from 'react';
import styles from './SidebarRight.module.css';
import { FormRequest } from '../types/form';
import FormMessage from './FormMessage';

export interface RequestMessage {
    id: number;
    role: 'user' | 'ai';
    content: string;
    form?: FormRequest;
}

interface SidebarRightProps {
    messages: RequestMessage[];
    input: string;
    onInputChange: (value: string) => void;
    onSendMessage: (e: React.FormEvent) => void;
}

export default function SidebarRight({ messages, input, onInputChange, onSendMessage }: SidebarRightProps) {
    const handleOptionSelect = (sectionTitle: string, value: string) => {
        // For now, we'll just log it or simulate sending a message
        console.log(`Selected option in ${sectionTitle}: ${value}`);
        // potentially call onInputChange or onSendMessage with the selected value
        onInputChange(value);
    };

    return (
        <aside className={styles.sidebar}>
            <div className={styles.header}>
                <h2>Assistant</h2>
            </div>
            <div className={styles.chatContainer}>
                {messages.map((msg) => (
                    <div key={msg.id} className={`${styles.message} ${styles[msg.role]}`}>
                        <div className={styles.bubble}>
                            {msg.content}
                            {msg.form && (
                                <FormMessage
                                    data={msg.form}
                                    onOptionSelect={handleOptionSelect}
                                />
                            )}
                        </div>
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
