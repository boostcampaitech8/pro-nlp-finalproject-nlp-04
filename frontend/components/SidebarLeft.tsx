import styles from './SidebarLeft.module.css';

const MOCK_RESEARCH = [
    { id: 1, title: 'Notion API Documentation', type: 'link', url: 'https://developers.notion.com/' },
    { id: 2, title: 'Tiptap Editor Guide', type: 'link', url: 'https://tiptap.dev/introduction' },
    { id: 3, title: 'Vercel AI SDK', type: 'link', url: 'https://sdk.vercel.ai/docs' },
    { id: 4, title: 'React Performance Optimization', type: 'pdf', url: '#' },
];

export default function SidebarLeft() {
    return (
        <aside className={styles.sidebar}>
            <div className={styles.header}>
                <h2>Info</h2>
                <button className={styles.addButton}>+</button>
            </div>
            <div className={styles.section}>
                <h3>Research Materials</h3>
                <ul className={styles.list}>
                    {MOCK_RESEARCH.map((item) => (
                        <li key={item.id} className={styles.item}>
                            <span className={styles.icon}>{item.type === 'link' ? '🔗' : '📄'}</span>
                            <span className={styles.title}>{item.title}</span>
                        </li>
                    ))}
                </ul>
            </div>
        </aside>
    );
}
