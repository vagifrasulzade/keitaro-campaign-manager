import type { ComponentProps, ReactNode } from "react";

export const INPUT_CLASS =
  "w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm outline-none " +
  "focus:border-green-500 focus:ring-2 focus:ring-green-100 disabled:bg-gray-50 disabled:text-gray-400";

export const LINK_CLASS = "text-green-700 hover:underline";

type ButtonVariant = "primary" | "secondary" | "danger";
type ButtonSize = "sm" | "md";

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-1 whitespace-nowrap rounded border font-medium " +
  "transition-colors disabled:cursor-not-allowed disabled:opacity-45";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "border-transparent bg-green-500 text-white hover:bg-green-600 disabled:hover:bg-green-500",
  secondary: "border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:hover:bg-white",
  danger: "border-red-300 bg-white text-red-600 hover:bg-red-50 disabled:hover:bg-white",
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "px-2 py-1 text-xs",
  md: "px-4 py-2 text-sm",
};

interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export function Button({ variant = "secondary", size = "md", type = "button", className = "", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
      {...props}
    />
  );
}

type TagTone = "gray" | "green" | "red";

const TAG_TONES: Record<TagTone, string> = {
  gray: "bg-gray-100 text-gray-600",
  green: "bg-green-100 text-green-700",
  red: "bg-red-100 text-red-700",
};

export function Tag({ tone = "gray", children }: { tone?: TagTone; children: ReactNode }) {
  return <span className={`inline-block rounded px-1.5 text-xs leading-5 ${TAG_TONES[tone]}`}>{children}</span>;
}

interface CardProps extends ComponentProps<"section"> {
  /** amber border for a card with unpublished changes */
  highlight?: boolean;
}

export function Card({ highlight = false, className = "", ...props }: CardProps) {
  const border = highlight ? "border-amber-300 ring-2 ring-amber-50" : "border-gray-200";
  return <section className={`rounded-lg border bg-white p-5 ${border} ${className}`} {...props} />;
}

interface FieldProps {
  label: string;
  htmlFor: string;
  hint?: ReactNode;
  children: ReactNode;
}

export function Field({ label, htmlFor, hint, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-gray-700">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </div>
  );
}
