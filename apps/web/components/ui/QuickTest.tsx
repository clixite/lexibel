"use client";

/**
 * Quick Test Component
 * Test rapide de tous les composants premium
 */

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
import { Heart } from "lucide-react";

export default function QuickTest() {
  const [showModal, setShowModal] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const tabs = [
    { id: "1", label: "Tab 1", content: <div>Content 1</div> },
    { id: "2", label: "Tab 2", badge: 5, content: <div>Content 2</div> },
  ];

  return (
    <div className="p-8 space-y-8 bg-neutral-50">
      <h1 className="text-3xl font-display font-bold">Quick Component Test</h1>

      {/* Buttons */}
      <div className="flex gap-2">
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
        <Button variant="primary" loading>
          Loading
        </Button>
        <Button variant="primary" icon={<Heart className="w-4 h-4" />}>
          Icon
        </Button>
      </div>

      {/* Input */}
      <div className="max-w-md">
        <Input label="Test Input" placeholder="Type here..." />
        <Input label="With Error" error="This is an error message" />
      </div>

      {/* Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <p>Simple Card</p>
        </Card>
        <Card hover>
          <p>Hover Card</p>
        </Card>
        <Card header={<h3>Header</h3>} footer={<p>Footer</p>}>
          <p>Full Card</p>
        </Card>
      </div>

      {/* Badges */}
      <div className="flex gap-2">
        <Badge variant="default">Default</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="warning">Warning</Badge>
        <Badge variant="danger">Danger</Badge>
        <Badge variant="accent" dot>
          Dot
        </Badge>
        <Badge variant="success" dot pulse>
          Pulse
        </Badge>
      </div>

      {/* Avatars */}
      <div className="flex gap-4">
        <Avatar fallback="A" size="sm" />
        <Avatar fallback="B" size="md" status="online" />
        <Avatar fallback="C" size="lg" status="busy" />
        <Avatar fallback="D" size="xl" status="offline" />
      </div>

      {/* Tooltips */}
      <div className="flex gap-4">
        <Tooltip content="Top" position="top">
          <Button variant="secondary">Top</Button>
        </Tooltip>
        <Tooltip content="Bottom" position="bottom">
          <Button variant="secondary">Bottom</Button>
        </Tooltip>
      </div>

      {/* Tabs */}
      <Card>
        <Tabs tabs={tabs} />
      </Card>

      {/* Modal & Toast Triggers */}
      <div className="flex gap-4">
        <Button variant="primary" onClick={() => setShowModal(true)}>
          Open Modal
        </Button>
        <Button variant="secondary" onClick={() => setShowToast(true)}>
          Show Toast
        </Button>
      </div>

      {/* Skeletons */}
      <div className="space-y-2">
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="circle" width="48px" height="48px" />
        <Skeleton variant="rect" width="100%" height="80px" />
      </div>

      {/* Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Test Modal"
        footer={
          <Button variant="primary" onClick={() => setShowModal(false)}>
            Close
          </Button>
        }
      >
        <p>This is a test modal content.</p>
      </Modal>

      {/* Toast */}
      {showToast && (
        <Toast
          message="Test toast message"
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}
