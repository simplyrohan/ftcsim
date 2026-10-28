import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
export function cn(...inputs:ClassValue[]) { return twMerge(clsx(inputs)); }
export type WithoutChild<T> = T extends {child?:any} ? Omit<T,'child'> : T;
export type WithoutChildren<T> = T extends {children?:any} ? Omit<T,'children'> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T,E extends HTMLElement = HTMLElement> = T & {ref?:E|null};
export const format = (value:unknown,digits=2) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits}) : '—';
export const pretty = (value:string) => value.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
