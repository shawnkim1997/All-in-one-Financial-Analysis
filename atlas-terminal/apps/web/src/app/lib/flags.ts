export const flags = {
  newDataGateway: process.env.NEXT_PUBLIC_FLAG_GATEWAY === "true",
  peerCompare: process.env.NEXT_PUBLIC_FLAG_PEER === "true",
  earningsDelta: process.env.NEXT_PUBLIC_FLAG_EARNINGS === "true",
  calendar: process.env.NEXT_PUBLIC_FLAG_CALENDAR === "true",
  financials: process.env.NEXT_PUBLIC_FLAG_FINANCIALS === "true",
  ownership: process.env.NEXT_PUBLIC_FLAG_OWNERSHIP === "true",
  correlation: process.env.NEXT_PUBLIC_FLAG_CORR === "true",
  cgt: process.env.NEXT_PUBLIC_FLAG_CGT === "true",
  redteam: process.env.NEXT_PUBLIC_FLAG_REDTEAM === "true",
} as const;
