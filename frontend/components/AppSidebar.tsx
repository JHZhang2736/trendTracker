"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BarChart3, Brain, LayoutDashboard, Search, Settings } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { CollectButton } from "@/components/CollectButton"

const navItems: { title: string; href: string; icon: LucideIcon }[] = [
  { title: "仪表盘", href: "/", icon: LayoutDashboard },
  { title: "趋势列表", href: "/trends", icon: BarChart3 },
  { title: "AI 洞察", href: "/ai", icon: Brain },
  { title: "深度分析", href: "/deep-analysis", icon: Search },
  { title: "系统设置", href: "/settings", icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg">TrendTracker</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">全网趋势聚合 · AI商业洞察</p>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>导航</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    isActive={pathname === item.href}
                    render={<Link href={item.href} />}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4">
        <CollectButton />
      </SidebarFooter>
    </Sidebar>
  )
}
