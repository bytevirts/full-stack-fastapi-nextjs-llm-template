{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
"use client";

import { useEffect, useState } from "react";
import { useConversations } from "@/hooks";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import {
  MessageSquarePlus,
  MessageSquare,
  Trash2,
  Archive,
  MoreVertical,
  Pencil,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type { Conversation } from "@/types";

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onRename: (title: string) => void;
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
  onArchive,
  onRename,
}: ConversationItemProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(conversation.title || "");

  const handleRename = () => {
    if (editTitle.trim()) {
      onRename(editTitle.trim());
    }
    setIsEditing(false);
  };

  const displayTitle =
    conversation.title ||
    `Chat ${new Date(conversation.created_at).toLocaleDateString()}`;

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer",
        isActive
          ? "bg-secondary text-secondary-foreground"
          : "text-muted-foreground hover:bg-secondary/50 hover:text-secondary-foreground"
      )}
      onClick={onSelect}
    >
      <MessageSquare className="h-4 w-4 shrink-0" />
      {isEditing ? (
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onBlur={handleRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleRename();
            if (e.key === "Escape") setIsEditing(false);
          }}
          className="flex-1 bg-transparent outline-none text-foreground"
          autoFocus
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="flex-1 truncate">{displayTitle}</span>
      )}

      <div className="relative">
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "h-6 w-6 p-0 opacity-0 group-hover:opacity-100",
            showMenu && "opacity-100"
          )}
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
        >
          <MoreVertical className="h-3.5 w-3.5" />
        </Button>

        {showMenu && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowMenu(false)}
            />
            <div className="absolute right-0 top-6 z-20 w-36 rounded-md border bg-popover shadow-lg">
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditing(true);
                  setShowMenu(false);
                }}
              >
                <Pencil className="h-3.5 w-3.5" />
                Rename
              </button>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  onArchive();
                  setShowMenu(false);
                }}
              >
                <Archive className="h-3.5 w-3.5" />
                Archive
              </button>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                  setShowMenu(false);
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

interface ConversationSidebarProps {
  className?: string;
}

export function ConversationSidebar({ className }: ConversationSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const {
    conversations,
    currentConversationId,
    isLoading,
    fetchConversations,
    selectConversation,
    deleteConversation,
    archiveConversation,
    renameConversation,
    startNewChat,
  } = useConversations();

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const activeConversations = conversations.filter((c) => !c.is_archived);

  if (isCollapsed) {
    return (
      <div
        className={cn(
          "flex flex-col items-center border-r bg-background py-4 w-12",
          className
        )}
      >
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 mb-4"
          onClick={() => setIsCollapsed(false)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={startNewChat}
          title="New Chat"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <aside
      className={cn(
        "flex w-64 shrink-0 flex-col border-r bg-background",
        className
      )}
    >
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="font-semibold text-sm">Conversations</h2>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setIsCollapsed(true)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      <div className="p-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={startNewChat}
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {isLoading && conversations.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            Loading...
          </div>
        ) : activeConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-sm text-muted-foreground">
            <MessageSquare className="h-8 w-8 mb-2 opacity-50" />
            <p>No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          <div className="space-y-1">
            {activeConversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === currentConversationId}
                onSelect={() => selectConversation(conversation.id)}
                onDelete={() => deleteConversation(conversation.id)}
                onArchive={() => archiveConversation(conversation.id)}
                onRename={(title) => renameConversation(conversation.id, title)}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
{%- else %}
// Conversation sidebar - not configured (enable_conversation_persistence is false)
{%- endif %}
