'use client';

import React from 'react';
import { FormRequest, FormSection, FormOption } from '../types/form';
import styles from './FormMessage.module.css';

interface FormMessageProps {
    data: FormRequest;
    onOptionSelect: (sectionTitle: string, value: string) => void;
}

export default function FormMessage({ data, onOptionSelect }: FormMessageProps) {
    if (!data || !data.forms) return null;

    return (
        <div className={styles.container}>
            {data.forms.map((section, index) => (
                <div key={`${section.current_section}-${index}`} className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <span className={styles.sectionTitle}>{section.current_section}</span>
                        <p className={styles.question}>{section.question}</p>
                    </div>

                    <div className={styles.options}>
                        {section.options.map((option, optIndex) => (
                            <button
                                key={`${option.value}-${optIndex}`}
                                className={styles.optionButton}
                                onClick={() => onOptionSelect(section.current_section, option.value)}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>

                    {section.guide_text && (
                        <div className={styles.guideText}>
                            💡 {section.guide_text}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
