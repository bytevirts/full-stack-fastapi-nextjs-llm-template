"use client";

import { useEffect, useRef, useCallback } from "react";
import { useChat, useLocalChat } from "@/hooks";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { Button } from "@/components/ui";
import { Wifi, WifiOff, RotateCcw, Bot } from "lucide-react";

function LocalChatContainer() {
  const {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
  } = useLocalChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}
      clearMessages={clearMessages}
      messagesEndRef={messagesEndRef}
    />
  );
}
export function ChatContainer() {
  return <LocalChatContainer />;
}

interface ChatUIProps {
  messages: import("@/types").ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  sendMessage: (content: string) => void;
  clearMessages: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  sendMessage,
  clearMessages,
  messagesEndRef,
}: ChatUIProps) {
  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
      <div className="flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-secondary flex items-center justify-center">
              <Bot className="h-7 w-7 sm:h-8 sm:w-8" />
            </div>
            <div className="text-center px-4">
              <p className="text-base sm:text-lg font-medium text-foreground">AI Assistant</p>
              <p className="text-sm">Start a conversation to get help</p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="px-2 pb-2 sm:px-4 sm:pb-4">
        <div className="rounded-xl border bg-card shadow-sm p-3 sm:p-4">
          <ChatInput
            onSend={sendMessage}
            disabled={!isConnected || isProcessing}
            isProcessing={isProcessing}
          />
          <div className="flex items-center justify-between mt-3 pt-3 border-t">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <Wifi className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-red-500" />
              )}
              <span className="text-xs text-muted-foreground">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearMessages}
              className="text-xs h-8 px-3"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              Reset
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
