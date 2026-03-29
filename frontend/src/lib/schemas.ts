import { z } from "zod";

export const searchFormSchema = z.object({
  query: z
    .string()
    .min(3, "Search query must be at least 3 characters")
    .max(200, "Search query is too long"),
});

export type SearchFormValues = z.infer<typeof searchFormSchema>;
