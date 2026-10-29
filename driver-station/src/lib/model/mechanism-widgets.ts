import type { Component } from 'svelte';
import type { MechanismState } from './types';
import CustomMechanismView from '$lib/components/CustomMechanismView.svelte';
import MecanumView from '$lib/components/MecanumView.svelte';
// New mechanism kinds register a Svelte counterpart here, independently of drivers.
export const mechanismWidgets = new Map<string,Component<{mechanism:MechanismState}>>([['mecanum',MecanumView],['custom',CustomMechanismView]]);
