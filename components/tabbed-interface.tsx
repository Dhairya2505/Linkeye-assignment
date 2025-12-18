"use client"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ChatTab } from "./chat-tab"
import { ContextTab } from "./context-tab"


export function TabbedInterface() {
    

  return (
    <div className="h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-4xl h-full max-h-screen flex flex-col bg-card rounded-lg border border-border shadow-lg">
        <Tabs defaultValue="ask" className="w-full h-full flex flex-col">
          <TabsList className="w-full rounded-none border-b border-border bg-secondary">
            <TabsTrigger
              value="ask"
              className="flex-1 rounded-none data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              Ask Questions
            </TabsTrigger>
            <TabsTrigger
              value="context"
              className="flex-1 rounded-none data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              Provide Context
            </TabsTrigger>
          </TabsList>

          <TabsContent value="ask" className="flex-1 m-0">
            <ChatTab />
          </TabsContent>

          <TabsContent value="context" className="flex-1 m-0">
            <ContextTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
