import { AibMessage } from "@/lib/aib-api";

interface MessageBubbleProps {
  message: AibMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  return (
    <div
      className={`flex gap-2 ${isAssistant ? "justify-start" : "justify-end"}`}
    >
      {isAssistant && (
        <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
          <span className="text-white text-[10px] font-bold">T</span>
        </div>
      )}
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
          isAssistant
            ? "bg-surface border border-border text-foreground rounded-tl-sm"
            : "bg-primary text-white rounded-tr-sm"
        }`}
      >
        {message.content}
        {isAssistant &&
          Object.keys(message.extracted_fields).length > 0 && (
            <div className="mt-1.5 pt-1.5 border-t border-border/50 flex flex-wrap gap-1">
              {Object.keys(message.extracted_fields).map((key) => (
                <span
                  key={key}
                  className="text-[10px] bg-success/10 text-success px-1.5 py-0.5 rounded-full"
                >
                  ✓ {key.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}
