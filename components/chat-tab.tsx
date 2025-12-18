"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send } from "lucide-react"
import axios from "axios"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import Link from "next/link"

interface Message {
  id: string
  text: string
  top_anchor_id: String | null,
  score: number | null
  sender: "user" | "assistant"
  timestamp: Date
}

export default function MarkdownViewer({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {content}
    </ReactMarkdown>
  )
}

export function ChatTab() {

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I'm here to help. Ask me anything!",
      top_anchor_id: null,
      score: null,
      sender: "assistant",
      timestamp: new Date(),
    },
  ])

  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      top_anchor_id: null,
      score: null,
      sender: "user",
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response: {
        data: {
          answer: string,
          top_anchor_id: string,
          score: number        
        }
      } = await axios.post("http://127.0.0.1:8000/get-answer", {
        query: input
      })
      console.log(response)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.answer || "Sorry, I couldn't process your request.",
        top_anchor_id: response.data.top_anchor_id,
        score: response.data.score,
        sender: "assistant",
        timestamp: new Date()
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error:", error)
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        text: "An error occurred. Please try again.",
        top_anchor_id: null,
        score: null,
        sender: "assistant",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex-1 p-6 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-xs lg:max-w-md overflow-auto px-4 py-2 rounded-lg ${
                message.sender === "user"
                  ? "bg-primary text-primary-foreground rounded-br-none"
                  : "bg-secondary text-secondary-foreground rounded-bl-none"
              }`}
            >
              <p className="text-sm">
                <MarkdownViewer content={message.text} />
                {message.top_anchor_id &&
                  <Link href={`https://api.freshservice.com/#${message.top_anchor_id}`} className="text-blue-500 underline" target="_blank">
                  Reference
                </Link>}
                {message.score &&
                  <div>
                  Score - {message.score}
                </div>}
              </p>
              <span className="text-xs opacity-70">
                {message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-secondary text-secondary-foreground px-4 py-2 rounded-lg">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border p-4 bg-background">
        <div className="flex gap-2">
          <Input
            type="text"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            className="flex-1"
          />
          <Button onClick={handleSendMessage} disabled={isLoading || !input.trim()} className="gap-2">
            <Send className="w-4 h-4" />
            Send
          </Button>
        </div>
      </div>
    </div>
  )
}
