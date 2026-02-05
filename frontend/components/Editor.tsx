'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import StarterKit from '@tiptap/starter-kit'
import ExtensionBubbleMenu from '@tiptap/extension-bubble-menu'
import Image from '@tiptap/extension-image'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import styles from './Editor.module.css'

interface EditorProps {
    content?: string
    onAskAI?: (text: string) => void
    onImageClick?: () => void
}

const Editor = ({ content = '<p>Start typing...</p>', onAskAI, onImageClick }: EditorProps) => {
    const editor = useEditor({
        extensions: [
            StarterKit,
            ExtensionBubbleMenu,
            Image.configure({
                inline: true,
                allowBase64: true,
                HTMLAttributes: {
                    class: styles.editorImage,
                },
            }),
            Table.configure({
                resizable: true,
                HTMLAttributes: {
                    class: styles.editorTable,
                },
            }),
            TableRow,
            TableCell,
            TableHeader,
        ],
        content,
        editorProps: {
            attributes: {
                class: styles.editorInput,
            },
        },
        immediatelyRender: false,
        autofocus: 'end',
    })

    // Prevent hydration mismatch
    if (!editor) {
        return null
    }

    return (
        <div className={styles.editorWrapper}>
            {editor && (
                <BubbleMenu className={styles.bubbleMenu} editor={editor}>
                    <button
                        onClick={() => {
                            const { from, to } = editor.state.selection
                            const text = editor.state.doc.textBetween(from, to, ' ')
                            if (text && onAskAI) {
                                onAskAI(text)
                            }
                        }}
                        className={styles.askAIButton}
                    >
                        ✨ Ask AI
                    </button>
                    <button
                        onClick={() => {
                            if (onImageClick) {
                                onImageClick()
                            }
                        }}
                        className={styles.askAIButton}
                        style={{ marginLeft: '8px' }}
                    >
                        🎨 Generate
                    </button>
                </BubbleMenu>
            )}
            <EditorContent editor={editor} />
        </div>
    )
}

export default Editor
