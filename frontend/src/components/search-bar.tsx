"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { searchFormSchema, type SearchFormValues } from "@/lib/schemas";

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SearchFormValues>({
    resolver: zodResolver(searchFormSchema),
    defaultValues: { query: "" },
  });

  function onSubmit(data: SearchFormValues) {
    onSearch(data.query);
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
    </form>
  );
}
