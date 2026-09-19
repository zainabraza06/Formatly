import type { SVGProps } from 'react'

/**
 * One icon set, one weight, one grid. Every icon is 20×20 with a 1.6 stroke so
 * they sit on the same optical line as 13–15px text, and every one is
 * aria-hidden: an icon is never the only name for a control.
 */
type IconProps = SVGProps<SVGSVGElement>

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-4 w-4"
      {...props}
    >
      {children}
    </svg>
  )
}

export const DocumentsIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M11.5 2.5H5.75A1.25 1.25 0 0 0 4.5 3.75v12.5a1.25 1.25 0 0 0 1.25 1.25h8.5a1.25 1.25 0 0 0 1.25-1.25V6.5z" />
    <path d="M11.5 2.5V6.5h4M7.5 10.5h5M7.5 13.5h5" />
  </Icon>
)

export const ComposeIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9.5 3.5 10.6 6.4 13.5 7.5 10.6 8.6 9.5 11.5 8.4 8.6 5.5 7.5 8.4 6.4z" />
    <path d="M14.5 12.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6zM4.5 12.5l.5 1.1 1.1.5-1.1.5-.5 1.1-.5-1.1L3 14.1l1-.5z" />
  </Icon>
)

export const EditorIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 4.5h13M3.5 8.5h8M3.5 12.5h5" />
    <path d="M12.8 15.9 16.9 11.8a1.2 1.2 0 0 0-1.7-1.7l-4.1 4.1-.4 2.1z" />
  </Icon>
)

export const SettingsIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="2.4" />
    <path d="M10 2.5l1 1.9a6.6 6.6 0 0 1 1.7 1l2.1-.3 1 1.8-1.3 1.7a6.6 6.6 0 0 1 0 2l1.3 1.7-1 1.8-2.1-.3a6.6 6.6 0 0 1-1.7 1l-1 1.9h-2l-1-1.9a6.6 6.6 0 0 1-1.7-1l-2.1.3-1-1.8 1.3-1.7a6.6 6.6 0 0 1 0-2L3.2 6.9l1-1.8 2.1.3a6.6 6.6 0 0 1 1.7-1l1-1.9z" />
  </Icon>
)

export const SearchIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="9" cy="9" r="5.25" />
    <path d="m13 13 3.5 3.5" />
  </Icon>
)

export const PlusIcon = (p: IconProps) => (
  <Icon {...p}><path d="M10 4.5v11M4.5 10h11" /></Icon>
)

export const UploadIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 13.5V3.5M6.5 7 10 3.5 13.5 7" />
    <path d="M3.5 13v2.25a1.25 1.25 0 0 0 1.25 1.25h10.5a1.25 1.25 0 0 0 1.25-1.25V13" />
  </Icon>
)

export const DownloadIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 3.5v10M6.5 10 10 13.5 13.5 10" />
    <path d="M3.5 13v2.25a1.25 1.25 0 0 0 1.25 1.25h10.5a1.25 1.25 0 0 0 1.25-1.25V13" />
  </Icon>
)

export const MoreIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="4.5" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="10" cy="10" r="1.1" fill="currentColor" stroke="none" />
    <circle cx="10" cy="15.5" r="1.1" fill="currentColor" stroke="none" />
  </Icon>
)

export const TrashIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 5.5h13M8 5.5V4a.75.75 0 0 1 .75-.75h2.5A.75.75 0 0 1 12 4v1.5" />
    <path d="M5.5 5.5 6.2 16a.9.9 0 0 0 .9.85h5.8a.9.9 0 0 0 .9-.85l.7-10.5M8.5 8.5v5M11.5 8.5v5" />
  </Icon>
)

export const CopyIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="7" y="7" width="9.5" height="9.5" rx="1.4" />
    <path d="M13 4.75A1.25 1.25 0 0 0 11.75 3.5H4.75A1.25 1.25 0 0 0 3.5 4.75v7A1.25 1.25 0 0 0 4.75 13" />
  </Icon>
)

export const CheckIcon = (p: IconProps) => (
  <Icon {...p}><path d="m4.5 10.5 3.5 3.5 7.5-8" /></Icon>
)

export const CloseIcon = (p: IconProps) => (
  <Icon {...p}><path d="m5 5 10 10M15 5 5 15" /></Icon>
)

export const UndoIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 5.5 3.5 9 7 12.5" />
    <path d="M3.5 9h7.75A4.25 4.25 0 0 1 15.5 13.25v0a4.25 4.25 0 0 1-4.25 4.25H8" />
  </Icon>
)

export const ChevronLeftIcon = (p: IconProps) => (
  <Icon {...p}><path d="M12 5 7 10l5 5" /></Icon>
)

export const ChevronRightIcon = (p: IconProps) => (
  <Icon {...p}><path d="m8 5 5 5-5 5" /></Icon>
)

export const ChevronDownIcon = (p: IconProps) => (
  <Icon {...p}><path d="m5 8 5 5 5-5" /></Icon>
)

export const MenuIcon = (p: IconProps) => (
  <Icon {...p}><path d="M3.5 5.5h13M3.5 10h13M3.5 14.5h13" /></Icon>
)

export const SidebarIcon = (p: IconProps) => (
  <Icon {...p}>
    <rect x="3" y="4" width="14" height="12" rx="1.6" />
    <path d="M8 4v12" />
  </Icon>
)

export const SunIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="3.25" />
    <path d="M10 2.5v1.75M10 15.75v1.75M17.5 10h-1.75M4.25 10H2.5M15.3 4.7l-1.24 1.24M5.94 14.06 4.7 15.3M15.3 15.3l-1.24-1.24M5.94 5.94 4.7 4.7" />
  </Icon>
)

export const MoonIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M16.5 12.4A7 7 0 0 1 7.6 3.5a7 7 0 1 0 8.9 8.9z" />
  </Icon>
)

export const SignOutIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12.5 13.5v1.75a1.25 1.25 0 0 1-1.25 1.25h-6A1.25 1.25 0 0 1 4 15.25V4.75A1.25 1.25 0 0 1 5.25 3.5h6a1.25 1.25 0 0 1 1.25 1.25V6.5" />
    <path d="M8.5 10h8M14 7.5 16.5 10 14 12.5" />
  </Icon>
)

export const SparkIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 3.5 11.3 7.2 15 8.5l-3.7 1.3L10 13.5 8.7 9.8 5 8.5l3.7-1.3z" />
    <path d="M15 13.5l.55 1.45L17 15.5l-1.45.55L15 17.5l-.55-1.45L13 15.5l1.45-.55z" />
  </Icon>
)

export const WarningIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10 3.5 17.5 16.5h-15z" />
    <path d="M10 8v3.5M10 14.2v.3" />
  </Icon>
)

export const FileIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="M11.5 2.5H6.25A1.25 1.25 0 0 0 5 3.75v12.5a1.25 1.25 0 0 0 1.25 1.25h7.5A1.25 1.25 0 0 0 15 16.25V6z" />
    <path d="M11.5 2.5V6H15" />
  </Icon>
)

export const ClockIcon = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="10" cy="10" r="6.75" />
    <path d="M10 6v4.2l2.6 1.6" />
  </Icon>
)

export const LayersIcon = (p: IconProps) => (
  <Icon {...p}>
    <path d="m10 3 6.5 3.4L10 9.8 3.5 6.4z" />
    <path d="m3.5 10 6.5 3.4 6.5-3.4M3.5 13.6 10 17l6.5-3.4" />
  </Icon>
)
