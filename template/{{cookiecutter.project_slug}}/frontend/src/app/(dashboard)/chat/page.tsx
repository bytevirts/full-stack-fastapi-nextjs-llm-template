{%- if cookiecutter.enable_conversation_persistence and cookiecutter.use_database %}
import { ChatContainer, ConversationSidebar } from "@/components/chat";

export default function ChatPage() {
  return (
    <div className="flex h-full">
      <ConversationSidebar />
      <div className="flex-1 min-w-0">
        <ChatContainer />
      </div>
    </div>
  );
}
{%- else %}
import { ChatContainer } from "@/components/chat";

export default function ChatPage() {
  return <ChatContainer />;
}
{%- endif %}
