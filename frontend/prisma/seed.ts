import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash(
    "Admin@123",
    12
  );

  await prisma.user.upsert({
    where: {
      email: "admin@bhudi.online",
    },
    update: {},
    create: {
      email: "admin@bhudi.online",
      passwordHash,
      firstName: "System",
      lastName: "Administrator",
      role: "SUPER_ADMIN",
    },
  });
}

main()
  .finally(async () => prisma.$disconnect());