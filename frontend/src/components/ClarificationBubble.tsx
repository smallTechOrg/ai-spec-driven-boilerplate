import { Message } from "@/lib/api";

interface Props {
  message: Message;
}

export default function ClarificationBubble({ message }: Props) {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-amber-50 border-l-4 border-amber-400 shadow-sm">
        <div className="flex items-start gap-2">
          <svg
            className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 3.042a1 1 0 01-.994.958V15m0 4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z"
            />
          </svg>
          <div>
            <p className="text-xs font-semibold text-amber-700 mb-1">Clarification needed</p>
            <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
          </div>
        </div>
        <p className="text-xs text-amber-600 mt-2 ml-6">
          Type your answer in the chat below to continue.
        </p>
      </div>
    </div>
  );
}
