'use client'

import { useState } from 'react';
import Editor from '../components/Editor'
import SidebarLeft from '../components/SidebarLeft';
import SidebarRight, { RequestMessage } from '../components/SidebarRight';
import TabBar, { Tab } from '../components/TabBar';
import ChangesView from '../components/ChangesView';
import AIModal from '../components/AIModal';

export default function Home() {
  const [messages, setMessages] = useState<RequestMessage[]>([
    { id: 1, role: 'ai', content: '안녕하세요! 기획서 작성을 도와드릴까요?' },
  ]);
  const [input, setInput] = useState('');

  // Tab state
  const [tabs, setTabs] = useState<Tab[]>([
    {
      id: 'doc-1',
      title: '바이브 기획서 프로젝트',
      type: 'document',
      content: `
            <p>이 문서는 <strong>Agentic AI</strong>를 활용한 소프트웨어 기획서 자동 생성 서비스의 초기 컨셉을 정의합니다.</p>
            <h2>1. 프로젝트 목표</h2>
            <ul>
              <li>Notion처럼 직관적인 문서 편집 경험 제공</li>
              <li>작성된 문서를 Context로 하여 AI가 코드 생성 및 프로젝트 관리 지원</li>
              <li><strong>"바이브(Vibe)"</strong>가 살아있는 프리미엄 UI/UX 구현</li>
            </ul>
            <h2>2. 핵심 기능</h2>
            <blockquote>
              모든 것은 텍스트에서 시작된다. 하지만 텍스트에 머물러서는 안 된다.
            </blockquote>
            <p>현재 구현된 기능:</p>
            <ul>
              <li>✅ Tiptap 기반 텍스트 에디터</li>
              <li>✅ Notion 스타일의 깔끔한 타이포그래피</li>
              <li>✅ 3단 레이아웃 (자료조사 - 에디터 - 챗봇)</li>
            </ul>
          `,
      isModified: false,
    },
    {
      id: 'changes',
      title: 'Changes',
      type: 'changes',
    },
  ]);
  const [activeTabId, setActiveTabId] = useState('doc-1');

  // AI Modal state
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [aiModalContext, setAIModalContext] = useState<'image' | 'table' | 'diagram' | 'search' | null>(null);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages([...messages, { id: Date.now(), role: 'user', content: input }]);
    setInput('');

    // Simulate AI response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'ai',
        content: '기획서 작성을 위해 몇 가지 정보가 필요합니다.',
        form: {
          message: "기획서 작성을 위해 몇 가지 정보가 필요합니다.",
          forms: [
            {
              current_section: "프로젝트 목적",
              question: "이 프로젝트의 주된 목적은 무엇인가요?",
              options: [
                { label: "신규 서비스 런칭", value: "new_launch" },
                { label: "기존 서비스 리뉴얼", value: "renewal" },
                { label: "내부 운영 효율화", value: "internal_ops" }
              ],
              guide_text: "프로젝트 성격에 따라 기획 방향이 달라질 수 있습니다."
            },
            {
              current_section: "타겟 사용자",
              question: "주요 타겟 사용자는 누구인가요?",
              options: [
                { label: "일반 대중 (B2C)", value: "b2c" },
                { label: "기업 고객 (B2B)", value: "b2b" },
                { label: "내부 임직원", value: "employee" }
              ],
              guide_text: "사용자 층에 따라 UI/UX 설계가 달라집니다."
            }
          ]
        }
      }]);
    }, 1000);
  };

  const handleAskAI = (selectedText: string) => {
    const prompt = `> ${selectedText}\n\n`;
    setInput(prompt);
  };

  const handleTabChange = (tabId: string) => {
    setActiveTabId(tabId);
  };

  const handleTabClose = (tabId: string) => {
    const newTabs = tabs.filter(tab => tab.id !== tabId);
    setTabs(newTabs);

    // If closing active tab, switch to another tab
    if (tabId === activeTabId && newTabs.length > 0) {
      setActiveTabId(newTabs[0].id);
    }
  };

  const handleNewTab = () => {
    const newTabId = `doc-${Date.now()}`;
    const newTab: Tab = {
      id: newTabId,
      title: 'Untitled',
      type: 'document',
      content: '<p>Start typing...</p>',
      isModified: false,
    };

    setTabs([...tabs.filter(t => t.type !== 'changes'), newTab, ...tabs.filter(t => t.type === 'changes')]);
    setActiveTabId(newTabId);
  };

  const handleContentChange = (content: string) => {
    setTabs(tabs.map(tab =>
      tab.id === activeTabId
        ? { ...tab, content, isModified: true }
        : tab
    ));
  };

  const handleTitleChange = (title: string) => {
    setTabs(tabs.map(tab =>
      tab.id === activeTabId
        ? { ...tab, title, isModified: true }
        : tab
    ));
  };

  const handleOpenAIModal = (contextType?: 'image' | 'table' | 'diagram' | 'search') => {
    setAIModalContext(contextType || null);
    setIsAIModalOpen(true);
  };

  const handleCloseAIModal = () => {
    setIsAIModalOpen(false);
    setAIModalContext(null);
  };

  const handleInsertContent = (content: any, type: 'image' | 'table' | 'diagram' | 'search') => {
    // This would require access to the editor instance, for now we'll just close the modal
    // In a real implementation, we'd pass this to the Editor component
    console.log('Insert content:', { content, type });
    // TODO: Implement actual content insertion
  };

  const activeTab = tabs.find(tab => tab.id === activeTabId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100vh', overflow: 'hidden' }}>
      <TabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onTabChange={handleTabChange}
        onTabClose={handleTabClose}
        onNewTab={handleNewTab}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <SidebarLeft />

        <main style={{
          flex: 1,
          padding: '40px 60px',
          overflowY: 'auto',
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column'
        }}>
          {activeTab?.type === 'changes' ? (
            <ChangesView documents={tabs} />
          ) : (
            <>
              <div style={{ marginBottom: '20px', maxWidth: '900px', margin: '0 auto 20px', width: '100%' }}>
                <input
                  type="text"
                  placeholder="Untitled"
                  value={activeTab?.title || ''}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  style={{
                    fontSize: '40px',
                    fontWeight: '700',
                    border: 'none',
                    outline: 'none',
                    width: '100%',
                    background: 'transparent',
                    color: 'inherit',
                    fontFamily: 'inherit'
                  }}
                />
              </div>
              <div style={{ flex: 1, maxWidth: '900px', margin: '0 auto', width: '100%' }}>
                <Editor
                  key={activeTabId}
                  content={activeTab?.content || '<p>Start typing...</p>'}
                  onAskAI={handleAskAI}
                  onImageClick={() => handleOpenAIModal('image')}
                />
              </div>
            </>
          )}
        </main>

        <SidebarRight
          messages={messages}
          input={input}
          onInputChange={setInput}
          onSendMessage={handleSendMessage}
        />
      </div>

      <AIModal
        isOpen={isAIModalOpen}
        onClose={handleCloseAIModal}
        onInsert={handleInsertContent}
        contextType={aiModalContext}
      />
    </div>
  );
}
