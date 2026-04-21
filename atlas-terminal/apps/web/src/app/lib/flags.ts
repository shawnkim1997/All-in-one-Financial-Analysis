export const flags = {
  newDataGateway: process.env.NEXT_PUBLIC_FLAG_GATEWAY === "true",
  peerCompare: process.env.NEXT_PUBLIC_FLAG_PEER === "true",
  earningsDelta: process.env.NEXT_PUBLIC_FLAG_EARNINGS === "true",
} as const;
