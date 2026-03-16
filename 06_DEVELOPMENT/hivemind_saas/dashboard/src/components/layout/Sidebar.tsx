"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Swords,
  GitBranch,
  Plug,
  Workflow,
  BookOpen,
  Users,
  CreditCard,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bell,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";

// ============================================================
// Types
// ============================================================
interface SidebarNavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  badge?: string | number;
  group: "main" | "tools" | "settings";
}

interface SidebarProps {
  user?: UserProfile;
}

// ============================================================
// Nav Item Configuration
// ============================================================
const NAV_ITEMS: SidebarNavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    group: "main",
  },
  {
    id: "war-room",
    label: "War Room",
    href: "/war-room",
    icon: Swords,
    badge: "4",
    group: "main",
  },
  {
    id: "mindmap",
    label: "Mindmap",
    href: "/mindmap",
    icon: GitBranch,
    group: "main",
  },
  {
    id: "integrations",
    label: "Integrations",
    href: "/integrations",
    icon: Plug,
    badge: "3",
    group: "tools",
  },
  {
    id: "workflows",
    label: "Workflows",
    href: "/workflows",
    icon: Workflow,
    group: "tools",
  },
  {
    id: "notebook",
    label: "Notebook",
    href: "/notebook",
    icon: BookOpen,
    group: "tools",
  },
  {
    id: "team",
    label: "Team",
    href: "/team",
    icon: Users,
    group: "tools",
  },
  {
    id: "billing",
    label: "Billing",
    href: "/billing",
    icon: CreditCard,
    group: "settings",
  },
  {
    id: "settings",
    label: "Settings",
    href: "/settings",
    icon: Settings,
    group: "settings",
  },
];

const MOCK_USER: UserProfile = {
  id: "usr_01",
  name: "Alex Rivera",
  email: "alex@company.com",
  plan: "pro",
  role: "Admin",
};

// ============================================================
// Sub-components
// ============================================================
function EverlightLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className={cn(
      "flex items-center gap-3 px-4 py-5",
      collapsed && "justify-center px-0"
    )}>
      {/* Logo mark */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
        style={{
          background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
          boxShadow: "0 0 16px rgba(124,58,237,0.4), inset 0 1px 0 rgba(255,255,255,0.15)",
        }}
      >
        <Sparkles size={16} strokeWidth={2} className="text-white" />
      </div>
      {!collapsed && (
        <div className="flex flex-col min-w-0">
          <span
            className="text-[15px] font-bold leading-none tracking-tight"
            style={{
              fontFamily: "'DM Sans', sans-serif",
              background: "linear-gradient(135deg, #A78BFA 0%, #7C3AED 50%, #F59E0B 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Everlight
          </span>
          <span className="text-[10px] font-semibold tracking-[0.12em] uppercase text-[#5C5C7A] mt-0.5">
            Hive Mind
          </span>
        </div>
      )}
    </div>
  );
}

function NavGroup({
  label,
  children,
  collapsed,
}: {
  label: string;
  children: React.ReactNode;
  collapsed: boolean;
}) {
  return (
    <div className="mb-1">
      {!collapsed && (
        <div className="px-4 mb-1.5">
          <span className="section-label">{label}</span>
        </div>
      )}
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function NavItemComponent({
  item,
  isActive,
  collapsed,
}: {
  item: SidebarNavItem;
  isActive: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        "nav-item mx-2",
        isActive && "active",
        collapsed && "justify-center px-0 mx-2"
      )}
      title={collapsed ? item.label : undefined}
    >
      <Icon
        size={17}
        strokeWidth={isActive ? 2.2 : 1.8}
        className={cn(
          "flex-shrink-0",
          isActive ? "text-violet-400" : "text-[#5C5C7A]"
        )}
      />
      {!collapsed && (
        <>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge && (
            <span
              className="flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
              style={{
                background: isActive
                  ? "rgba(124,58,237,0.2)"
                  : "rgba(255,255,255,0.06)",
                color: isActive ? "#A78BFA" : "#5C5C7A",
              }}
            >
              {item.badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}

function UserProfileSection({
  user,
  collapsed,
}: {
  user: UserProfile;
  collapsed: boolean;
}) {
  const planLabel = user.plan === "pro" ? "Pro" : user.plan === "team" ? "Team" : user.plan === "enterprise" ? "Enterprise" : "Starter";

  return (
    <div
      className={cn(
        "p-3 border-t border-[#1E1E2E]",
        collapsed ? "flex justify-center" : ""
      )}
    >
      <div
        className={cn(
          "flex items-center gap-3 p-2 rounded-xl cursor-pointer transition-colors hover:bg-white/[0.03]",
          collapsed && "justify-center"
        )}
      >
        {/* Avatar */}
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
          style={{
            background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
            boxShadow: "0 0 10px rgba(124,58,237,0.3)",
            color: "#F1F1F8",
          }}
        >
          {user.name.charAt(0)}
        </div>

        {!collapsed && (
          <>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-[#F1F1F8] truncate leading-none mb-1">
                {user.name}
              </p>
              <p className="text-[11px] text-[#5C5C7A] truncate leading-none">
                {user.email}
              </p>
            </div>
            <span className="badge badge-pro flex-shrink-0 text-[9px]">
              {planLabel}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Main Sidebar Component
// ============================================================
export default function Sidebar({ user = MOCK_USER }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const mainItems = NAV_ITEMS.filter((i) => i.group === "main");
  const toolItems = NAV_ITEMS.filter((i) => i.group === "tools");
  const settingItems = NAV_ITEMS.filter((i) => i.group === "settings");

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 z-40 flex flex-col transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
      style={{
        width: collapsed ? "72px" : "260px",
        background: "#0E0E16",
        borderRight: "1px solid #1E1E2E",
        boxShadow: "4px 0 24px rgba(0,0,0,0.4)",
      }}
    >
      {/* Logo */}
      <EverlightLogo collapsed={collapsed} />

      <hr className="divider mx-4 mb-3" />

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden no-scrollbar py-1">
        <NavGroup label="Workspace" collapsed={collapsed}>
          {mainItems.map((item) => (
            <NavItemComponent
              key={item.id}
              item={item}
              isActive={isActive(item.href)}
              collapsed={collapsed}
            />
          ))}
        </NavGroup>

        <div className="my-3 mx-4">
          <hr className="divider" />
        </div>

        <NavGroup label="Tools" collapsed={collapsed}>
          {toolItems.map((item) => (
            <NavItemComponent
              key={item.id}
              item={item}
              isActive={isActive(item.href)}
              collapsed={collapsed}
            />
          ))}
        </NavGroup>

        <div className="my-3 mx-4">
          <hr className="divider" />
        </div>

        <NavGroup label="Account" collapsed={collapsed}>
          {settingItems.map((item) => (
            <NavItemComponent
              key={item.id}
              item={item}
              isActive={isActive(item.href)}
              collapsed={collapsed}
            />
          ))}
        </NavGroup>
      </nav>

      {/* Notification bell (when expanded) */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[#5C5C7A] hover:bg-white/[0.04] transition-colors">
            <Bell size={16} strokeWidth={1.8} />
            <span className="text-[13px] font-medium flex-1 text-left">Notifications</span>
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: "rgba(124,58,237,0.2)", color: "#A78BFA" }}
            >
              5
            </span>
          </button>
        </div>
      )}

      {/* User profile */}
      <UserProfileSection user={user} collapsed={collapsed} />

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="absolute -right-3 top-[76px] w-6 h-6 rounded-full flex items-center justify-center transition-all hover:scale-110"
        style={{
          background: "#16161F",
          border: "1px solid #2A2A3E",
          boxShadow: "0 2px 8px rgba(0,0,0,0.4)",
          color: "#5C5C7A",
        }}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>
    </aside>
  );
}
