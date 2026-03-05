"use client";

import React from 'react';
import { Settings, HelpCircle, Info, Sun, Moon } from 'lucide-react';
import Link from 'next/link';

interface ModernHeaderProps {
  title?: string;
  userInfo?: {
    isAnonymous: boolean;
    name?: string;
  };
  onSettingsClick?: () => void;
  onHelpClick?: () => void;
  isDarkMode?: boolean;
  onThemeToggle?: () => void;
}

export default function ModernHeader({
  title = 'Deep Research Engine',
  userInfo,
  onSettingsClick,
  onHelpClick,
  isDarkMode = true,
  onThemeToggle,
}: ModernHeaderProps) {
  return (
    <header className="h-16 bg-[#111111] border-b border-[#2A2A2A] flex items-center justify-between px-6 sticky top-0 z-40 backdrop-blur-xl bg-opacity-80">
      {/* Left Side - Title and Version */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-gradient-to-br from-[#4F46E5] to-[#7C3AED] rounded-lg flex items-center justify-center">
          <span className="text-white font-bold">⚡</span>
        </div>
        <div>
          <h1 className="text-sm font-bold text-white">{title}</h1>
          <p className="text-xs text-[#A0A0A0]">v0.3 • Premium Research</p>
        </div>
      </div>

      {/* Right Side - User Info and Actions */}
      <div className="flex items-center gap-4">
        {userInfo && (
          <div className="text-right">
            <p className="text-xs text-[#A0A0A0]">
              {userInfo.isAnonymous ? '👤 Anonymous User' : `👤 ${userInfo.name}`}
            </p>
          </div>
        )}

        <div className="flex items-center gap-1.5">
          {/* Theme Toggle */}
          {onThemeToggle && (
            <button
              onClick={onThemeToggle}
              className="p-2 hover:bg-[#1A1A1A] rounded-lg transition-colors duration-200"
              title="Toggle theme"
            >
              {isDarkMode ? (
                <Moon className="w-4 h-4 text-[#A0A0A0]" />
              ) : (
                <Sun className="w-4 h-4 text-[#A0A0A0]" />
              )}
            </button>
          )}

          {/* About Link */}
          <Link
            href="/about"
            className="p-2 hover:bg-[#1A1A1A] rounded-lg transition-colors duration-200"
            title="About"
          >
            <Info className="w-4 h-4 text-[#A0A0A0]" />
          </Link>

          {/* Help Button */}
          {onHelpClick && (
            <button
              onClick={onHelpClick}
              className="p-2 hover:bg-[#1A1A1A] rounded-lg transition-colors duration-200"
              title="Help"
            >
              <HelpCircle className="w-4 h-4 text-[#A0A0A0]" />
            </button>
          )}

          {/* Settings Button */}
          {onSettingsClick && (
            <button
              onClick={onSettingsClick}
              className="p-2 hover:bg-[#1A1A1A] rounded-lg transition-colors duration-200"
              title="Settings"
            >
              <Settings className="w-4 h-4 text-[#A0A0A0]" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
