
"use client";

import { ChatContainer, LocalConversationSidebar, ChatSidebarToggle } from "@/components/chat";

export default function ChatPage() {
  return (
    <div className="flex h-full -m-3 sm:-m-6">
      <LocalConversationSidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="flex items-center gap-2 p-2 border-b md:hidden">
          <ChatSidebarToggle />
          <span className="text-sm font-medium">Chat</span>
        </div>
        <div className="flex-1 min-h-0">
          <ChatContainer />
        </div>
      </div>
    </div>
  );
}
