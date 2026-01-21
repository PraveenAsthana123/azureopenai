import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

interface Source {
  documentId: string;
  title: string;
  snippet: string;
  score: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface ChatStore {
  messages: Message[];
  conversations: Conversation[];
  currentConversationId: string | null;

  addMessage: (message: Message) => void;
  clearMessages: () => void;
  loadConversation: (conversationId: string) => void;
  createConversation: () => string;
  deleteConversation: (conversationId: string) => void;
  updateConversationTitle: (conversationId: string, title: string) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      messages: [],
      conversations: [],
      currentConversationId: null,

      addMessage: (message) => {
        const { messages, currentConversationId, conversations } = get();
        const newMessages = [...messages, message];

        set({ messages: newMessages });

        // Update conversation if exists
        if (currentConversationId) {
          const updatedConversations = conversations.map((conv) =>
            conv.id === currentConversationId
              ? {
                  ...conv,
                  messages: newMessages,
                  updatedAt: new Date(),
                  // Auto-generate title from first user message
                  title:
                    conv.title === 'New Conversation' && message.role === 'user'
                      ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                      : conv.title,
                }
              : conv
          );
          set({ conversations: updatedConversations });
        }
      },

      clearMessages: () => {
        const conversationId = get().createConversation();
        set({
          messages: [],
          currentConversationId: conversationId,
        });
      },

      loadConversation: (conversationId) => {
        const { conversations } = get();
        const conversation = conversations.find((c) => c.id === conversationId);

        if (conversation) {
          set({
            messages: conversation.messages,
            currentConversationId: conversationId,
          });
        }
      },

      createConversation: () => {
        const newConversation: Conversation = {
          id: `conv-${Date.now()}`,
          title: 'New Conversation',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };

        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          currentConversationId: newConversation.id,
        }));

        return newConversation.id;
      },

      deleteConversation: (conversationId) => {
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== conversationId),
          currentConversationId:
            state.currentConversationId === conversationId
              ? null
              : state.currentConversationId,
          messages:
            state.currentConversationId === conversationId ? [] : state.messages,
        }));
      },

      updateConversationTitle: (conversationId, title) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId ? { ...c, title } : c
          ),
        }));
      },
    }),
    {
      name: 'chat-store',
      partialize: (state) => ({
        conversations: state.conversations.slice(0, 50), // Keep last 50 conversations
      }),
    }
  )
);
