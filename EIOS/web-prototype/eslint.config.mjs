import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Design-system guardrails for the cockpit: colours come from cx-* tokens, type never drops below 11px.
const HEX_CLASS = '-\\[#[0-9a-fA-F]{3,8}\\]';
const MICRO_TEXT = '\\btext-\\[(?:[0-9]|10)px\\]';
const guard = (pattern, message) => [
  { selector: `Literal[value=/${pattern}/]`, message },
  { selector: `TemplateElement[value.raw=/${pattern}/]`, message },
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      'react-hooks/purity': 'warn',
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs': 'warn',
      'react-hooks/immutability': 'warn',
      'react/display-name': 'warn',
      '@typescript-eslint/no-unused-vars': 'warn',
    },
  },
  {
    files: ['src/components/cockpit/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': [
        'error',
        ...guard(HEX_CLASS, 'Use a cx-* design token from globals.css instead of a raw hex Tailwind class.'),
        ...guard(MICRO_TEXT, 'Minimum text size is 11px: use text-label (11px) or text-title (13px).'),
      ],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
