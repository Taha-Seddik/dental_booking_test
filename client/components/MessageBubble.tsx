import clsx from "clsx";

type Props = {
  sender: "user" | "assistant";
  text: string;
};

export default function MessageBubble({ sender, text }: Props) {
  const isUser = sender === "user";

  return (
    <div
      className={clsx(
        "flex mb-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "max-w-xs md:max-w-md px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap",
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-white text-slate-800 border rounded-bl-sm"
        )}
      >
        {text}
      </div>
    </div>
  );
}
