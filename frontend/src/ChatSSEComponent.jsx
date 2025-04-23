import React, { useState, useRef } from "react";

export default function ChatSSEComponent() {
  const [question, setQuestion] = useState("");
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const eventSourceRef = useRef(null);

  const startChat = async () => {
    setIsLoading(true);
    setOutput("");

    // We first create a fetch POST to get the session started
    const response = await fetch("/api/chat/stream/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    const read = async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n");
        for (let line of lines) {
          if (line.startsWith("data: ")) {
            setOutput((prev) => prev + line.replace("data: ", "") + "\n");
          }
        }
      }
      setIsLoading(false);
    };

    read();
  };

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">🧠 Chain-of-Thought Agent</h2>
      <textarea
        rows="4"
        className="w-full p-2 border rounded mb-2"
        placeholder="Ask your question here..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button
        className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        onClick={startChat}
        disabled={isLoading || question.trim() === ""}
      >
        {isLoading ? "Thinking..." : "Ask"}
      </button>
      <pre className="mt-4 p-2 bg-gray-100 rounded overflow-auto whitespace-pre-wrap">
        {output}
      </pre>
    </div>
  );
}
