import type { ComponentType } from 'react';
import { AccordionDemo } from './demos/accordion';
import { AlertDemo } from './demos/alert';
import { AlertDialogDemo } from './demos/alert-dialog';
import { AspectRatioDemo } from './demos/aspect-ratio';
import { AvatarDemo } from './demos/avatar';
import { BadgeDemo } from './demos/badge';
import { BreadcrumbDemo } from './demos/breadcrumb';
import { ButtonDemo } from './demos/button';
import { ButtonGroupDemo } from './demos/button-group';
import { CalendarDemo } from './demos/calendar';
import { CardDemo } from './demos/card';
import { CarouselDemo } from './demos/carousel';
import { ChartDemo } from './demos/chart';
import { CheckboxDemo } from './demos/checkbox';
import { CollapsibleDemo } from './demos/collapsible';
import { CommandDemo } from './demos/command';
import { ContextMenuDemo } from './demos/context-menu';
import { DialogDemo } from './demos/dialog';
import { DrawerDemo } from './demos/drawer';
import { DropdownMenuDemo } from './demos/dropdown-menu';
import { EmptyDemo } from './demos/empty';
import { FieldDemo } from './demos/field';
import { FormDemo } from './demos/form';
import { HoverCardDemo } from './demos/hover-card';
import { InputDemo } from './demos/input';
import { InputGroupDemo } from './demos/input-group';
import { InputOtpDemo } from './demos/input-otp';
import { ItemDemo } from './demos/item';
import { KbdDemo } from './demos/kbd';
import { MenubarDemo } from './demos/menubar';
import { NavigationMenuDemo } from './demos/navigation-menu';
import { PaginationDemo } from './demos/pagination';
import { PopoverDemo } from './demos/popover';
import { ProgressDemo } from './demos/progress';
import { RadioGroupDemo } from './demos/radio-group';
import { ResizableDemo } from './demos/resizable';
import { ScrollAreaDemo } from './demos/scroll-area';
import { SelectDemo } from './demos/select';
import { SeparatorDemo } from './demos/separator';
import { SheetDemo } from './demos/sheet';
import { SidebarDemo } from './demos/sidebar';
import { SkeletonDemo } from './demos/skeleton';
import { SliderDemo } from './demos/slider';
import { SonnerDemo } from './demos/sonner';
import { SpinnerDemo } from './demos/spinner';
import { SwitchDemo } from './demos/switch';
import { TableDemo } from './demos/table';
import { TabsDemo } from './demos/tabs';
import { TextareaDemo } from './demos/textarea';
import { ToastDemo } from './demos/toast';
import { ToggleDemo } from './demos/toggle';
import { ToggleGroupDemo } from './demos/toggle-group';
import { TooltipDemo } from './demos/tooltip';
import {
  ColorsPage,
  FontsPage,
  LayoutPage,
  OverviewPage,
} from './foundations';

export type PreviewEntry = {
  // Globally unique across every group — it is the deep-link slug (`#page=<id>`)
  // and the active-page key. Group-qualify names that repeat across groups
  // (e.g. `brand-icons` vs `components-icons`).
  id: string;
  name: string;
  description: string;
  Page: ComponentType;
};

export type NavGroup = {
  name: string;
  entries: PreviewEntry[];
};

export const DESIGN_SYSTEM = {
  title: 'Design System',
  description:
    'A reusable system of foundations, components, and patterns for product surfaces.',
} as const;

export const OVERVIEW_ENTRY: PreviewEntry = {
  id: 'overview',
  name: 'Overview',
  description: 'The visual foundations and principles that shape this system.',
  Page: OverviewPage,
};

export const NAV_GROUPS: NavGroup[] = [
  { name: 'Brand', entries: [] },
  {
    name: 'Colors',
    entries: [
      {
        id: 'color-roles',
        name: 'Color roles',
        description: 'Brand, semantic, text, background, and border colors.',
        Page: ColorsPage,
      },
    ],
  },
  {
    name: 'Fonts',
    entries: [
      {
        id: 'type-scale',
        name: 'Type scale',
        description: 'Font families, headings, body text, labels, and captions.',
        Page: FontsPage,
      },
    ],
  },
  {
    name: 'Layout',
    entries: [
      {
        id: 'spacing-radius',
        name: 'Spacing and radius',
        description: 'The spacing rhythm and corner treatments used by the system.',
        Page: LayoutPage,
      },
    ],
  },
  {
    name: 'Actions',
    entries: [
      {
        id: 'button',
        name: 'Buttons',
        description: 'Button variants, sizes, icon treatments, and states.',
        Page: ButtonDemo,
      },
      {
        id: 'button-group',
        name: 'Button group',
        description: 'Attached actions, labels, and separators.',
        Page: ButtonGroupDemo,
      },
      {
        id: 'toggle',
        name: 'Toggle',
        description: 'Pressed controls in multiple variants and sizes.',
        Page: ToggleDemo,
      },
      {
        id: 'toggle-group',
        name: 'Toggle group',
        description: 'Single and multiple selection toggle sets.',
        Page: ToggleGroupDemo,
      },
    ],
  },
  {
    name: 'Forms & inputs',
    entries: [
      {
        id: 'input',
        name: 'Input',
        description: 'Text, email, file, and validation states.',
        Page: InputDemo,
      },
      {
        id: 'input-group',
        name: 'Input group',
        description: 'Inputs with inline and block addons.',
        Page: InputGroupDemo,
      },
      {
        id: 'input-otp',
        name: 'Input OTP',
        description: 'Segmented one-time code entry.',
        Page: InputOtpDemo,
      },
      {
        id: 'textarea',
        name: 'Textarea',
        description: 'Multiline text entry and states.',
        Page: TextareaDemo,
      },
      {
        id: 'checkbox',
        name: 'Checkbox',
        description: 'Checked, unchecked, and disabled options.',
        Page: CheckboxDemo,
      },
      {
        id: 'radio-group',
        name: 'Radio group',
        description: 'Exclusive choices with labels and disabled states.',
        Page: RadioGroupDemo,
      },
      {
        id: 'select',
        name: 'Select',
        description: 'Selection controls, grouped options, and disabled states.',
        Page: SelectDemo,
      },
      {
        id: 'slider',
        name: 'Slider',
        description: 'Single values, ranges, and disabled states.',
        Page: SliderDemo,
      },
      {
        id: 'switch',
        name: 'Switch',
        description: 'Binary preference controls and states.',
        Page: SwitchDemo,
      },
      {
        id: 'calendar',
        name: 'Calendar',
        description: 'A deterministic single-date calendar.',
        Page: CalendarDemo,
      },
      {
        id: 'field',
        name: 'Field',
        description: 'Labels, descriptions, errors, and grouped fields.',
        Page: FieldDemo,
      },
      {
        id: 'form',
        name: 'Form',
        description: 'Validated form composition with labels and messages.',
        Page: FormDemo,
      },
    ],
  },
  {
    name: 'Overlays',
    entries: [
      {
        id: 'dialog',
        name: 'Dialog',
        description: 'Modal content with header, footer, and actions.',
        Page: DialogDemo,
      },
      {
        id: 'alert-dialog',
        name: 'Alert dialog',
        description: 'Confirmation for consequential actions.',
        Page: AlertDialogDemo,
      },
      {
        id: 'sheet',
        name: 'Sheet',
        description: 'Edge-aligned overlay panels.',
        Page: SheetDemo,
      },
      {
        id: 'drawer',
        name: 'Drawer',
        description: 'Touch-friendly bottom overlay content.',
        Page: DrawerDemo,
      },
      {
        id: 'popover',
        name: 'Popover',
        description: 'Anchored interactive content.',
        Page: PopoverDemo,
      },
      {
        id: 'hover-card',
        name: 'Hover card',
        description: 'Rich context revealed on hover.',
        Page: HoverCardDemo,
      },
      {
        id: 'tooltip',
        name: 'Tooltip',
        description: 'Brief labels for focused or hovered controls.',
        Page: TooltipDemo,
      },
      {
        id: 'command',
        name: 'Command',
        description: 'Searchable keyboard-first command lists.',
        Page: CommandDemo,
      },
    ],
  },
  {
    name: 'Menus & navigation',
    entries: [
      {
        id: 'dropdown-menu',
        name: 'Dropdown menu',
        description: 'Actions, choices, shortcuts, and submenus.',
        Page: DropdownMenuDemo,
      },
      {
        id: 'context-menu',
        name: 'Context menu',
        description: 'Right-click actions and nested choices.',
        Page: ContextMenuDemo,
      },
      {
        id: 'menubar',
        name: 'Menubar',
        description: 'Desktop-style application menus.',
        Page: MenubarDemo,
      },
      {
        id: 'navigation-menu',
        name: 'Navigation menu',
        description: 'Primary navigation with rich flyouts.',
        Page: NavigationMenuDemo,
      },
      {
        id: 'breadcrumb',
        name: 'Breadcrumb',
        description: 'Hierarchical location and parent links.',
        Page: BreadcrumbDemo,
      },
      {
        id: 'pagination',
        name: 'Pagination',
        description: 'Previous, next, page, and overflow controls.',
        Page: PaginationDemo,
      },
      {
        id: 'tabs',
        name: 'Tabs',
        description: 'Switch between related content views.',
        Page: TabsDemo,
      },
      {
        id: 'sidebar',
        name: 'Sidebar',
        description: 'Bounded application navigation and content layout.',
        Page: SidebarDemo,
      },
    ],
  },
  {
    name: 'Data display',
    entries: [
      {
        id: 'avatar',
        name: 'Avatar',
        description: 'Profile images, fallbacks, and sizes.',
        Page: AvatarDemo,
      },
      {
        id: 'badge',
        name: 'Badge',
        description: 'Compact status and category labels.',
        Page: BadgeDemo,
      },
      {
        id: 'card',
        name: 'Card',
        description: 'Grouped content with header, body, and footer.',
        Page: CardDemo,
      },
      {
        id: 'table',
        name: 'Table',
        description: 'Structured tabular data and summaries.',
        Page: TableDemo,
      },
      {
        id: 'accordion',
        name: 'Accordion',
        description: 'Expandable sections for progressive disclosure.',
        Page: AccordionDemo,
      },
      {
        id: 'collapsible',
        name: 'Collapsible',
        description: 'A compact expandable content region.',
        Page: CollapsibleDemo,
      },
      {
        id: 'carousel',
        name: 'Carousel',
        description: 'Keyboard-accessible paged content.',
        Page: CarouselDemo,
      },
      {
        id: 'item',
        name: 'Item',
        description: 'Flexible rows with media, metadata, and actions.',
        Page: ItemDemo,
      },
      {
        id: 'empty',
        name: 'Empty state',
        description: 'Guidance and actions when content is absent.',
        Page: EmptyDemo,
      },
      {
        id: 'kbd',
        name: 'Keyboard key',
        description: 'Individual and grouped keyboard shortcuts.',
        Page: KbdDemo,
      },
      {
        id: 'aspect-ratio',
        name: 'Aspect ratio',
        description: 'Responsive proportional media containers.',
        Page: AspectRatioDemo,
      },
    ],
  },
  {
    name: 'Feedback',
    entries: [
      {
        id: 'alert',
        name: 'Alert',
        description: 'Informational and destructive messages.',
        Page: AlertDemo,
      },
      {
        id: 'progress',
        name: 'Progress',
        description: 'Completion indicators for ongoing work.',
        Page: ProgressDemo,
      },
      {
        id: 'skeleton',
        name: 'Skeleton',
        description: 'Placeholder shapes for loading content.',
        Page: SkeletonDemo,
      },
      {
        id: 'spinner',
        name: 'Spinner',
        description: 'Indeterminate loading indicators.',
        Page: SpinnerDemo,
      },
      {
        id: 'toast',
        name: 'Toast',
        description: 'Provider-backed transient notifications and actions.',
        Page: ToastDemo,
      },
      {
        id: 'sonner',
        name: 'Sonner',
        description: 'Stacked notifications with status and actions.',
        Page: SonnerDemo,
      },
    ],
  },
  {
    name: 'Structure',
    entries: [
      {
        id: 'separator',
        name: 'Separator',
        description: 'Horizontal and vertical visual dividers.',
        Page: SeparatorDemo,
      },
      {
        id: 'scroll-area',
        name: 'Scroll area',
        description: 'Bounded vertical and horizontal scrolling.',
        Page: ScrollAreaDemo,
      },
      {
        id: 'resizable',
        name: 'Resizable panels',
        description: 'Bounded split panes with draggable handles.',
        Page: ResizableDemo,
      },
    ],
  },
  { name: 'Content', entries: [] },
  {
    name: 'Charts',
    entries: [
      {
        id: 'chart',
        name: 'Chart',
        description: 'Configured data visualization, tooltip, and legend.',
        Page: ChartDemo,
      },
    ],
  },
  { name: 'Motion', entries: [] },
  { name: 'Applied examples', entries: [] },
];

export const ALL_ENTRIES: PreviewEntry[] = [
  OVERVIEW_ENTRY,
  ...NAV_GROUPS.flatMap((group) => group.entries),
];

// A duplicate id would make one page unreachable (its deep link and highlight
// resolve to the first match), so fail loudly instead of shipping a dead page.
const duplicateIds = ALL_ENTRIES.map((entry) => entry.id).filter(
  (id, index, ids) => ids.indexOf(id) !== index,
);
if (duplicateIds.length > 0) {
  throw new Error(
    `Duplicate preview page id(s): ${[...new Set(duplicateIds)].join(
      ', ',
    )}. Every page id must be unique across all nav groups.`,
  );
}
