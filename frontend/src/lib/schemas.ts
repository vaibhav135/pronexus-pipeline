import { z } from "zod";

export const searchFormSchema = z.object({
  query: z
    .string()
    .min(3, "Search query must be at least 3 characters")
    .max(200, "Search query is too long"),
  limit: z.string().refine((v) => {
    const n = parseInt(v, 10);
    return !isNaN(n) && n >= 1 && n <= 200;
  }, "Must be between 1 and 200"),
  lat: z.string(),
  lng: z.string(),
});

export type SearchFormValues = z.infer<typeof searchFormSchema>;
