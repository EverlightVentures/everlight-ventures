'use client';

import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge, Button } from '@everlight/ui';
import type { Contact } from '@everlight/db';

export function ContactsTable({
  contacts,
  projectSlug,
}: {
  contacts: Contact[];
  projectSlug: string;
}) {
  const [search, setSearch] = useState('');

  const filteredContacts = contacts.filter((contact) => {
    const searchLower = search.toLowerCase();
    return (
      contact.email.toLowerCase().includes(searchLower) ||
      contact.firstName?.toLowerCase().includes(searchLower) ||
      contact.lastName?.toLowerCase().includes(searchLower) ||
      contact.company?.toLowerCase().includes(searchLower)
    );
  });

  if (contacts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No contacts yet. Add your first contact or import from CSV.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <input
          type="search"
          placeholder="Search contacts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-gray-300 px-4 py-2"
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Tags</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredContacts.map((contact) => (
            <TableRow key={contact.id}>
              <TableCell>
                {contact.firstName || contact.lastName
                  ? `${contact.firstName || ''} ${contact.lastName || ''}`.trim()
                  : '-'}
              </TableCell>
              <TableCell>{contact.email}</TableCell>
              <TableCell>{contact.company || '-'}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  {contact.tags.slice(0, 2).map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                  {contact.tags.length > 2 && (
                    <Badge variant="secondary">+{contact.tags.length - 2}</Badge>
                  )}
                </div>
              </TableCell>
              <TableCell>
                {contact.subscribed ? (
                  <Badge variant="success">Subscribed</Badge>
                ) : (
                  <Badge variant="secondary">Unsubscribed</Badge>
                )}
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="sm">
                  Edit
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {filteredContacts.length === 0 && search && (
        <div className="text-center py-8 text-gray-500">
          No contacts found matching "{search}"
        </div>
      )}
    </div>
  );
}
