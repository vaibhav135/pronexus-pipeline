"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Search, Loader2, ChevronDown, Settings2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { searchFormSchema, type SearchFormValues } from "@/lib/schemas";
import type { SearchRequest } from "@/lib/types";

interface SearchBarProps {
  onSearch: (req: SearchRequest) => void;
  isLoading?: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SearchFormValues>({
    resolver: zodResolver(searchFormSchema),
    defaultValues: { query: "", limit: "20", lat: "", lng: "" },
  });

  function onSubmit(data: SearchFormValues) {
    onSearch({
      query: data.query,
      limit: parseInt(data.limit, 10),
      lat: data.lat || undefined,
      lng: data.lng || undefined,
    });
    reset();
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex flex-col gap-2 w-full max-w-2xl"
    >
      <div className="relative flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted/60" />
          <Input
            {...register("query")}
            placeholder='e.g. "HVAC contractor Houston TX"'
            className="h-12 pl-10 text-base bg-surface border-border shadow-sm focus-visible:ring-primary/30"
            disabled={isLoading}
          />
        </div>
        <Button
          type="submit"
          disabled={isLoading}
          className="h-12 px-6 bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm shadow-primary/20"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            "Search"
          )}
        </Button>
      </div>

      {errors.query && (
        <p className="text-sm text-error pl-1">{errors.query.message}</p>
      )}

      <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
        <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors pl-1">
          <Settings2 className="h-3 w-3" />
          Advanced options
          <ChevronDown
            className={`h-3 w-3 transition-transform ${advancedOpen ? "rotate-180" : ""}`}
          />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-3 grid grid-cols-3 gap-3 rounded-lg border border-border bg-surface p-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-muted">
                Results limit
              </label>
              <Input
                type="number"
                {...register("limit")}
                className="h-9 text-sm"
                disabled={isLoading}
              />
              {errors.limit && (
                <p className="text-xs text-error">{errors.limit.message}</p>
              )}
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-muted">
                Latitude
              </label>
              <Input
                {...register("lat")}
                placeholder="e.g. 29.7604"
                className="h-9 text-sm"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-muted">
                Longitude
              </label>
              <Input
                {...register("lng")}
                placeholder="e.g. -95.3698"
                className="h-9 text-sm"
                disabled={isLoading}
              />
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </form>
  );
}
