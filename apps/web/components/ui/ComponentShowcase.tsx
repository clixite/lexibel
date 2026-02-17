"use client";

import { useState } from "react";
import {
  Button,
  Input,
  Card,
  Badge,
  Modal,
  Tooltip,
  Avatar,
  Tabs,
  Toast,
  Skeleton,
} from "./index";
import { Search, Heart, User, Settings, Mail, Bell } from "lucide-react";

export default function ComponentShowcase() {
  const [showModal, setShowModal] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const tabs = [
    {
      id: "overview",
      label: "Overview",
      icon: <User className="w-4 h-4" />,
      content: <div>Overview content goes here</div>,
    },
    {
      id: "settings",
      label: "Settings",
      icon: <Settings className="w-4 h-4" />,
      badge: 3,
      content: <div>Settings content goes here</div>,
    },
    {
      id: "notifications",
      label: "Notifications",
      icon: <Bell className="w-4 h-4" />,
      badge: 12,
      content: <div>Notifications content goes here</div>,
    },
  ];

  return (
    <div className="p-8 space-y-12 bg-neutral-50 min-h-screen">
      <div>
        <h1 className="text-3xl font-display font-bold text-primary-900 mb-2">
          LexiBel Premium UI Components
        </h1>
        <p className="text-neutral-600">
          Design system showcase avec tous les composants premium
        </p>
      </div>

      {/* Buttons */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Buttons
        </h2>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="ghost">Ghost Button</Button>
            <Button variant="danger">Danger Button</Button>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary" size="sm">
              Small
            </Button>
            <Button variant="primary" size="md">
              Medium
            </Button>
            <Button variant="primary" size="lg">
              Large
            </Button>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary" icon={<Heart className="w-4 h-4" />}>
              With Icon
            </Button>
            <Button variant="primary" loading>
              Loading...
            </Button>
            <Button variant="primary" disabled>
              Disabled
            </Button>
          </div>
        </div>
      </section>

      {/* Inputs */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Inputs
        </h2>
        <div className="max-w-md space-y-4">
          <Input label="Email" placeholder="Enter your email" type="email" />
          <Input
            label="Search"
            placeholder="Search..."
            prefixIcon={<Search className="w-4 h-4" />}
          />
          <Input
            label="Password"
            placeholder="Enter password"
            type="password"
            suffixIcon={<Mail className="w-4 h-4" />}
          />
          <Input
            label="Error Example"
            placeholder="Invalid input"
            error="This field is required"
          />
        </div>
      </section>

      {/* Cards */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Cards
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <h3 className="font-semibold text-lg mb-2">Simple Card</h3>
            <p className="text-neutral-600">Basic card with content</p>
          </Card>
          <Card hover>
            <h3 className="font-semibold text-lg mb-2">Hover Card</h3>
            <p className="text-neutral-600">Hover me to see the effect</p>
          </Card>
          <Card
            header={<h3 className="font-semibold">With Header</h3>}
            footer={<Button variant="primary">Action</Button>}
          >
            <p className="text-neutral-600">Card with header and footer</p>
          </Card>
        </div>
      </section>

      {/* Badges */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Badges
        </h2>
        <div className="flex flex-wrap gap-3">
          <Badge variant="default">Default</Badge>
          <Badge variant="success">Success</Badge>
          <Badge variant="warning">Warning</Badge>
          <Badge variant="danger">Danger</Badge>
          <Badge variant="accent">Accent</Badge>
          <Badge variant="neutral">Neutral</Badge>
        </div>
        <div className="flex flex-wrap gap-3 mt-4">
          <Badge variant="success" dot>
            With Dot
          </Badge>
          <Badge variant="danger" dot pulse>
            Pulsing
          </Badge>
          <Badge variant="accent" size="sm">
            Small
          </Badge>
          <Badge variant="accent" size="md">
            Medium
          </Badge>
        </div>
      </section>

      {/* Avatars */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Avatars
        </h2>
        <div className="flex flex-wrap gap-4 items-end">
          <Avatar fallback="JD" size="sm" />
          <Avatar fallback="AB" size="md" status="online" />
          <Avatar fallback="XY" size="lg" status="busy" />
          <Avatar fallback="MN" size="xl" status="offline" />
        </div>
      </section>

      {/* Tooltips */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Tooltips
        </h2>
        <div className="flex flex-wrap gap-4">
          <Tooltip content="Top tooltip" position="top">
            <Button variant="secondary">Hover Top</Button>
          </Tooltip>
          <Tooltip content="Bottom tooltip" position="bottom">
            <Button variant="secondary">Hover Bottom</Button>
          </Tooltip>
          <Tooltip content="Left tooltip" position="left">
            <Button variant="secondary">Hover Left</Button>
          </Tooltip>
          <Tooltip content="Right tooltip" position="right">
            <Button variant="secondary">Hover Right</Button>
          </Tooltip>
        </div>
      </section>

      {/* Tabs */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Tabs
        </h2>
        <Card>
          <Tabs tabs={tabs} defaultTab="overview" />
        </Card>
      </section>

      {/* Modal & Toast */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Modal & Toast
        </h2>
        <div className="flex gap-4">
          <Button variant="primary" onClick={() => setShowModal(true)}>
            Open Modal
          </Button>
          <Button variant="secondary" onClick={() => setShowToast(true)}>
            Show Toast
          </Button>
        </div>

        <Modal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          title="Example Modal"
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setShowModal(false)}>
                Confirm
              </Button>
            </div>
          }
        >
          <p className="text-neutral-600">
            This is a premium modal with backdrop blur, animations, and
            keyboard support. Press ESC to close.
          </p>
        </Modal>

        {showToast && (
          <Toast
            message="Operation completed successfully"
            type="success"
            onClose={() => setShowToast(false)}
          />
        )}
      </section>

      {/* Skeletons */}
      <section>
        <h2 className="text-2xl font-display font-semibold text-primary-900 mb-4">
          Skeletons
        </h2>
        <div className="space-y-4">
          <div className="space-y-2">
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="80%" />
            <Skeleton variant="text" width="40%" />
          </div>
          <div className="flex gap-4 items-center">
            <Skeleton variant="circle" width="48px" height="48px" />
            <div className="flex-1 space-y-2">
              <Skeleton variant="text" width="30%" />
              <Skeleton variant="rect" width="100%" height="60px" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
