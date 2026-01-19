import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

export default function AccountSwitcher({ 
  accounts = [] as string[], 
  onSelect = (_a: string) => {},
  className = ''
}: { 
  accounts?: string[]; 
  onSelect?: (a: string) => void;
  className?: string;
}) {
  if (accounts.length === 0) return null;

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <Select onValueChange={onSelect} defaultValue={accounts[0]}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Choose account" />
        </SelectTrigger>
        <SelectContent>
          {accounts.map(a => (
            <SelectItem key={a} value={a}>
              {a.slice(0, 6)}...{a.slice(-4)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

