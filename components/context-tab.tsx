"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import axios from "axios"

export function ContextTab() {
  const [isLoading, setIsLoading] = useState(false)
  const [responseText, setResponseText] = useState("")
  const [error, setError] = useState("")

  const handleProvideContext = async () => {
    setIsLoading(true)
    setError("")
    setResponseText("")

    try {
      const response = await axios.get("http://127.0.0.1:8000/ingest-data")

      const data = await response.data.message
      setResponseText(data || "Context provided successfully!")
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "An unknown error occurred"
      setError(errorMessage)
      console.error("Error:", err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-full flex items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Provide Context</CardTitle>
          <CardDescription>Click the button below to submit context data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleProvideContext} disabled={isLoading} className="w-full gap-2" size="lg">
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            {isLoading ? "Processing..." : "Provide Context"}
          </Button>

          {responseText && (
            <div className="p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
              <p className="text-sm font-medium text-green-900 dark:text-green-100 mb-2">Success</p>
              <p className="text-sm text-green-800 dark:text-green-200 break-words whitespace-pre-wrap">
                {responseText}
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm font-medium text-red-900 dark:text-red-100 mb-2">Error</p>
              <p className="text-sm text-red-800 dark:text-red-200 break-words">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
