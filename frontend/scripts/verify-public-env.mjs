const required = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
];

let missing = false;

for (const name of required) {
  const present = Boolean(process.env[name]?.trim());
  console.log(`[build-env] ${name}: ${present ? "SET" : "MISSING"}`);
  if (!present) missing = true;
}

if (missing) {
  console.error(
    "[build-env] Required public Supabase environment variables are missing. Configure them for the Vercel Production environment and redeploy."
  );
  process.exit(1);
}
