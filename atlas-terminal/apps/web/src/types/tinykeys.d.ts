declare module "tinykeys" {
  export type TinyKeysHandler = (event: KeyboardEvent) => void;
  export type TinyKeysKeyBindingMap = Record<string, TinyKeysHandler>;

  export function tinykeys(
    target: Window | Document | HTMLElement,
    keyBindingMap: TinyKeysKeyBindingMap,
    options?: { event?: string; capture?: boolean },
  ): () => void;
}
