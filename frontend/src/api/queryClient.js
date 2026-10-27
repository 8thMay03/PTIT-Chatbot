import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // API nội bộ: hiển thị lỗi ngay sau timeout 30 giây thay vì chờ thêm lượt retry.
      retry: 0,
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
});

export const queryKeys = {
  admin: ["admin"],
  adminSession: ["admin", "session"],
  auth: ["auth"],
  authMe: ["auth", "me"],
  config: ["config"],
  documents: ["documents"],
  documentList: ["documents", "list"],
  document: (documentId) => ["documents", "detail", documentId],
  documentChunks: (documentId, offset, limit) => [
    "documents",
    "chunks",
    documentId,
    offset,
    limit,
  ],
  documentAllChunks: (documentId) => ["documents", "chunks", documentId, "all"],
  documentParsers: (documentId) => ["documents", "parsers", documentId],
  parsersForFile: (fileName) => ["parsers", fileName],
  conversations: ["conversations"],
  conversationList: ["conversations", "list"],
  conversation: (conversationId) => [
    "conversations",
    "detail",
    conversationId,
  ],
};
