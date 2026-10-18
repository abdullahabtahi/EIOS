/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'next' {
  export type Metadata = {
    title?: string | { default: string; template: string };
    description?: string;
    icons?: any;
    [key: string]: any;
  };
  export type NextConfig = {
    [key: string]: any;
  };
}

declare module 'next/server' {
  export class NextRequest extends Request {
    readonly nextUrl: URL;
    readonly cookies: any;
    readonly ip?: string;
    readonly geo?: any;
    constructor(input: RequestInfo | URL, init?: RequestInit);
  }
  export class NextResponse extends Response {
    static json(body: any, init?: ResponseInit): NextResponse;
    static redirect(url: string | URL, status?: number): NextResponse;
    static rewrite(destination: string | URL): NextResponse;
    static next(): NextResponse;
    readonly cookies: any;
  }
}

declare module 'next/server.js' {
  export * from 'next/server';
}

declare module 'next/types.js' {
  export type ResolvingMetadata = Promise<any>;
  export type ResolvingViewport = Promise<any>;
}

declare module 'next/dist/build/segment-config/app/app-segment-config.js' {
  export type InstantConfigForTypeCheckInternal = any;
  export type Prefetch = any;
}

declare module 'next/dist/lib/metadata/types/metadata-interface.js' {
  export type ResolvingMetadata = Promise<any>;
  export type ResolvingViewport = Promise<any>;
}

declare module 'next/navigation' {
  export function useRouter(): {
    push(href: string, options?: any): void;
    replace(href: string, options?: any): void;
    refresh(): void;
    back(): void;
    forward(): void;
    prefetch(href: string): void;
  };
  export function usePathname(): string;
  export function useSearchParams(): URLSearchParams;
  export function useParams<T = Record<string, string | string[]>>(): T;
  export function notFound(): never;
  export function redirect(url: string): never;
}

declare module 'next/link' {
  import React from 'react';
  export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
    href: string | object;
    as?: string | object;
    replace?: boolean;
    scroll?: boolean;
    shallow?: boolean;
    passHref?: boolean;
    prefetch?: boolean;
    locale?: string | false;
  }
  const Link: React.ForwardRefExoticComponent<LinkProps & React.RefAttributes<HTMLAnchorElement>>;
  export default Link;
}

declare module 'next/font/google' {
  export function Inter(options?: any): { className: string; variable: string };
  export function JetBrains_Mono(options?: any): { className: string; variable: string };
  export function Schibsted_Grotesk(options?: any): { className: string; variable: string };
}
