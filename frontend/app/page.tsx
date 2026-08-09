"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export default function Home() {
  return (
    <div className="min-h-full w-full min-w-0 overflow-x-hidden bg-background text-foreground">
      <header className="bg-primary text-on-primary">
        <nav
          aria-label="Main navigation"
          className="mx-auto flex min-h-[72px] w-full max-w-7xl items-center justify-between gap-6 px-5 sm:px-8 lg:px-12"
        >
          <Link
            href="/"
            className="flex min-h-11 items-center gap-2 font-display text-xl font-extrabold tracking-[-0.04em]"
          >
            <div className="grid size-10 place-items-center rounded-[11px_11px_11px_4px] bg-surface shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="" className="size-8 object-contain" />
            </div>
            StoryBuddy
          </Link>

          <div className="flex items-center gap-7">
            <a
              href="#how-it-works"
              className="hidden min-h-11 items-center text-sm font-bold text-on-primary/85 transition-opacity hover:opacity-70 sm:flex"
            >
              How it works
            </a>
            <Link
              href="/signup"
              className="inline-flex min-h-11 items-center justify-center rounded-xl bg-secondary px-4 py-2 text-sm font-extrabold text-on-secondary shadow-[0_5px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_2px_0_var(--color-primary-deep)]"
            >
              Start writing
            </Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="grid lg:min-h-[calc(100dvh-72px)] lg:grid-cols-2">
          <div className="flex items-center bg-primary px-5 py-16 text-on-primary sm:px-8 sm:py-20 lg:px-12 xl:px-[max(3rem,calc((100vw-80rem)/2))] xl:pr-16">
            <motion.div 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="max-w-2xl"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="StoryBuddy" className="mb-8 h-16 w-auto object-contain sm:h-20 drop-shadow-[0_12px_24px_rgba(24,32,74,0.25)]" />
              <p className="mb-5 font-display text-sm font-extrabold tracking-[0.12em] text-secondary uppercase">
                Stories become keepsakes
              </p>
              <h1 className="max-w-[11ch] font-display text-5xl leading-[0.95] font-extrabold tracking-[-0.065em] text-balance sm:text-6xl lg:text-7xl xl:text-[5.5rem]">
                Big ideas. Bright pages.
              </h1>
              <p className="mt-6 max-w-[30rem] text-lg leading-8 text-[#DFE5FF] sm:text-xl">
                Write the adventure. StoryBuddy turns it into a picture book
                with familiar characters from page to page.
              </p>
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
                className="mt-8 flex flex-col items-stretch gap-4 sm:flex-row sm:items-center"
              >
                <Link
                  href="/signup"
                  className="inline-flex min-h-13 items-center justify-center rounded-xl bg-secondary px-6 py-3 font-extrabold text-on-secondary shadow-[0_7px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_3px_0_var(--color-primary-deep)]"
                >
                  Make a book
                </Link>
                <Link
                  href="/join"
                  className="inline-flex min-h-13 items-center justify-center rounded-xl border-2 border-secondary px-6 py-3 font-extrabold text-secondary transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5"
                >
                  I have a class code
                </Link>
              </motion.div>
            </motion.div>
          </div>

          <div className="relative grid min-h-[420px] place-items-center overflow-hidden bg-background px-4 py-10 sm:min-h-[520px] sm:px-8 md:min-h-full lg:px-12">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
              aria-hidden="true"
              className="pointer-events-none absolute top-[8%] right-[7%] size-36 rounded-full bg-secondary/80 sm:size-52"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.8, rotate: -40 }}
              animate={{ opacity: 1, scale: 1, rotate: -20 }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
              aria-hidden="true"
              className="pointer-events-none absolute bottom-[8%] left-[4%] h-40 w-24 rounded-[100%_0_100%_0] bg-[#A8C48E] sm:h-52 sm:w-32"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.8, rotate: 40 }}
              animate={{ opacity: 1, scale: 1, rotate: 24 }}
              transition={{ duration: 0.8, ease: "easeOut", delay: 0.3 }}
              aria-hidden="true"
              className="pointer-events-none absolute right-[2%] bottom-[4%] h-44 w-28 rounded-[100%_0_100%_0] bg-coral/75 sm:h-60 sm:w-36"
            />

            <motion.div
              initial={{ opacity: 0, y: 50, rotate: 0 }}
              animate={{ opacity: 1, y: 0, rotate: -3 }}
              transition={{ duration: 0.7, ease: "easeOut", delay: 0.2 }}
              className="relative z-10 aspect-[1.28/1] w-full max-w-[580px] drop-shadow-[0_28px_24px_rgba(24,32,74,0.2)]"
            >
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="w-full h-full"
              >
                <div className="absolute inset-y-0 left-0 w-[51%] overflow-hidden rounded-[20px_5px_9px_20px] border border-[#D8CEBB] bg-surface shadow-[inset_-12px_0_22px_rgba(24,32,74,0.08)]">
                  <div className="absolute inset-x-0 top-0 h-[58%] bg-[#DCE6F8]" />
                  <div className="absolute top-[15%] left-[15%] size-[18%] rounded-full bg-secondary" />
                  <div className="absolute right-[-22%] bottom-[-20%] h-[64%] w-[130%] rounded-[50%_50%_0_0] bg-[#739B7B]" />
                  <div className="absolute right-[-34%] bottom-[-24%] h-[49%] w-[122%] rounded-[50%_50%_0_0] bg-[#315F50]" />
                  <div className="absolute right-[15%] bottom-[18%] h-[24%] w-[20%] rounded-[44%] bg-coral">
                    <span className="absolute -top-[23%] left-[2%] h-[38%] w-[44%] rotate-[-10deg] bg-coral [clip-path:polygon(50%_0,100%_100%,0_100%)]" />
                    <span className="absolute -top-[23%] right-[2%] h-[38%] w-[44%] rotate-[10deg] bg-coral [clip-path:polygon(50%_0,100%_100%,0_100%)]" />
                    <span className="absolute top-[35%] left-[25%] size-[9%] rounded-full bg-foreground" />
                    <span className="absolute top-[35%] right-[25%] size-[9%] rounded-full bg-foreground" />
                  </div>
                </div>

                <div className="absolute inset-y-0 right-0 w-[51%] overflow-hidden rounded-[5px_20px_20px_9px] border border-[#D8CEBB] bg-surface px-[8%] py-[10%] shadow-[inset_12px_0_22px_rgba(24,32,74,0.08)]">
                  <div className="h-2.5 w-full rounded-full bg-[#DDD5C6]" />
                  <div className="mt-3 h-2.5 w-4/5 rounded-full bg-[#DDD5C6]" />
                  <div className="mt-3 h-2.5 w-[92%] rounded-full bg-[#DDD5C6]" />
                  <div className="mt-3 h-2.5 w-2/3 rounded-full bg-[#DDD5C6]" />
                  <p className="mt-[15%] font-display text-[clamp(0.85rem,2.2vw,1.55rem)] leading-[1.2] font-extrabold tracking-[-0.035em] text-primary">
                    Maya found a tiny door beneath the old mango tree.
                  </p>
                  <div className="absolute right-[12%] bottom-[11%] size-[17%] rounded-full bg-secondary/70" />
                </div>
                <div className="absolute top-[3%] bottom-[3%] left-1/2 w-px -translate-x-1/2 bg-[#C8BCA8] shadow-[0_0_12px_rgba(24,32,74,0.18)]" />
              </motion.div>
            </motion.div>
          </div>
        </section>

        <motion.section
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          id="how-it-works"
          className="scroll-mt-20 bg-background px-5 py-20 sm:px-8 sm:py-24 lg:px-12 lg:py-32"
        >
          <div className="mx-auto grid max-w-7xl gap-12 md:grid-cols-[0.8fr_1.2fr] md:gap-16 lg:gap-24">
            <div>
              <h2 className="max-w-[12ch] font-display text-4xl leading-[1.02] font-extrabold tracking-[-0.05em] sm:text-5xl">
                From first line to final page.
              </h2>
              <p className="mt-5 max-w-md text-lg leading-8 text-foreground/70">
                A simple path keeps the child focused on imagination, not the
                machinery behind it.
              </p>
            </div>

            <div className="border-t border-primary/20">
              <motion.div 
                whileHover={{ x: 8 }}
                className="grid gap-4 border-b border-primary/20 py-7 sm:grid-cols-[52px_1fr] sm:gap-6 transition-transform"
              >
                <span className="font-display text-lg font-extrabold text-primary">
                  01
                </span>
                <div>
                  <h3 className="font-display text-2xl font-extrabold tracking-[-0.035em]">
                    Write your story
                  </h3>
                  <p className="mt-2 max-w-xl leading-7 text-foreground/65">
                    Start with a few sentences or a whole adventure in your own
                    words.
                  </p>
                </div>
              </motion.div>
              <motion.div 
                whileHover={{ x: 8 }}
                className="grid gap-4 border-b border-primary/20 py-7 sm:grid-cols-[52px_1fr] sm:gap-6 transition-transform"
              >
                <span className="font-display text-lg font-extrabold text-primary">
                  02
                </span>
                <div>
                  <h3 className="font-display text-2xl font-extrabold tracking-[-0.035em]">
                    Meet your cast
                  </h3>
                  <p className="mt-2 max-w-xl leading-7 text-foreground/65">
                    Preview the main characters before their adventure becomes
                    a book.
                  </p>
                </div>
              </motion.div>
              <motion.div 
                whileHover={{ x: 8 }}
                className="grid gap-4 border-b border-primary/20 py-7 sm:grid-cols-[52px_1fr] sm:gap-6 transition-transform"
              >
                <span className="font-display text-lg font-extrabold text-primary">
                  03
                </span>
                <div>
                  <h3 className="font-display text-2xl font-extrabold tracking-[-0.035em]">
                    Read every page
                  </h3>
                  <p className="mt-2 max-w-xl leading-7 text-foreground/65">
                    Open the finished picture book and move through it at your
                    own pace.
                  </p>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.section>

        <motion.section 
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="bg-[#E9EDFC] px-5 py-20 sm:px-8 sm:py-24 lg:px-12 lg:py-32"
        >
          <div className="mx-auto grid max-w-7xl items-center gap-14 md:grid-cols-[1.05fr_0.95fr] lg:gap-24">
            <div className="relative min-h-[390px] sm:min-h-[480px]">
              <motion.div
                whileHover={{ scale: 1.02, rotate: -4, zIndex: 20 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                aria-hidden="true"
                className="absolute top-[2%] left-[3%] w-[66%] rotate-[-6deg] overflow-hidden rounded-2xl border border-primary/20 bg-surface shadow-[0_18px_40px_rgba(49,85,217,0.13)] cursor-default"
              >
                <div className="aspect-[4/3] bg-[#BCD5C0] p-[9%]">
                  <div className="relative h-full overflow-hidden rounded-xl bg-[#DCE6F8]">
                    <div className="absolute -right-[20%] -bottom-[35%] size-[105%] rounded-full bg-[#729B7B]" />
                    <div className="absolute bottom-[15%] left-[25%] h-[34%] w-[27%] rounded-[44%] bg-coral" />
                  </div>
                </div>
                <p className="p-4 font-kid text-sm font-bold">
                  The same brave fox, ready for the next page.
                </p>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.02, rotate: 3, zIndex: 20 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                aria-hidden="true"
                className="absolute right-[2%] bottom-[1%] w-[61%] rotate-[5deg] overflow-hidden rounded-2xl border border-primary/20 bg-surface shadow-[0_18px_40px_rgba(49,85,217,0.16)] cursor-default"
              >
                <div className="aspect-[4/3] bg-secondary/70 p-[9%]">
                  <div className="relative h-full overflow-hidden rounded-xl bg-[#B9C8F4]">
                    <div className="absolute -bottom-[42%] -left-[18%] size-[115%] rounded-full bg-primary" />
                    <div className="absolute right-[20%] bottom-[17%] h-[34%] w-[27%] rounded-[44%] bg-coral" />
                  </div>
                </div>
                <p className="p-4 font-kid text-sm font-bold">
                  New scene, familiar face, one continuous adventure.
                </p>
              </motion.div>
            </div>

            <div>
              <h2 className="max-w-[12ch] font-display text-4xl leading-[1.02] font-extrabold tracking-[-0.05em] sm:text-5xl">
                Familiar faces on every page.
              </h2>
              <p className="mt-6 max-w-xl text-lg leading-8 text-foreground/70">
                StoryBuddy carries the important details forward so a child can
                follow the same characters through changing scenes.
              </p>
              <a
                href="#safe-by-design"
                className="mt-7 inline-flex min-h-11 items-center font-extrabold text-primary underline decoration-primary/30 underline-offset-8 hover:decoration-primary transition-colors"
              >
                Built with care
              </a>
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          id="safe-by-design"
          className="scroll-mt-20 bg-background px-5 py-20 sm:px-8 sm:py-24 lg:px-12 lg:py-32"
        >
          <div className="mx-auto max-w-7xl rounded-3xl border border-primary/15 bg-surface p-7 shadow-[0_22px_60px_rgba(49,85,217,0.09)] sm:p-10 lg:grid lg:grid-cols-[1fr_0.9fr] lg:gap-20 lg:p-14">
            <div>
              <h2 className="max-w-[13ch] font-display text-4xl leading-[1.04] font-extrabold tracking-[-0.05em] sm:text-5xl">
                Made for young imaginations.
              </h2>
              <p className="mt-5 max-w-xl text-lg leading-8 text-foreground/70">
                Stories and pictures are checked before reading time, with clear
                choices if something needs another try.
              </p>
            </div>
            <div className="mt-10 border-t border-primary/15 lg:mt-0">
              <div className="border-b border-primary/15 py-5">
                <strong className="font-display text-lg">Preview first</strong>
                <p className="mt-1 leading-7 text-foreground/65">
                  Children meet the main characters before the pages are made.
                </p>
              </div>
              <div className="border-b border-primary/15 py-5">
                <strong className="font-display text-lg">Gentle recovery</strong>
                <p className="mt-1 leading-7 text-foreground/65">
                  Clear next steps replace technical errors and confusing
                  messages.
                </p>
              </div>
              <div className="py-5">
                <strong className="font-display text-lg">Comfortable reading</strong>
                <p className="mt-1 leading-7 text-foreground/65">
                  Large type, calm pages, and simple controls keep attention on
                  the story.
                </p>
              </div>
            </div>
          </div>
        </motion.section>

        <section className="bg-primary px-5 py-20 text-on-primary sm:px-8 sm:py-24 lg:px-12">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 md:flex-row md:items-end"
          >
            <div>
              <h2 className="max-w-[12ch] font-display text-4xl leading-[1.02] font-extrabold tracking-[-0.05em] sm:text-5xl">
                A new story starts here.
              </h2>
              <p className="mt-4 max-w-xl text-lg leading-8 text-[#DFE5FF]">
                Bring the words. StoryBuddy will help turn them into pages.
              </p>
            </div>
            <Link
              href="/signup"
              className="inline-flex min-h-13 shrink-0 items-center justify-center rounded-xl bg-secondary px-6 py-3 font-extrabold text-on-secondary shadow-[0_7px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_3px_0_var(--color-primary-deep)]"
            >
              Start your story
            </Link>
          </motion.div>
        </section>
      </main>

      <footer className="bg-foreground px-5 py-7 text-[#DCE2F6] sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 text-sm sm:flex-row sm:items-center sm:justify-between">
          <p className="font-bold text-surface">StoryBuddy</p>
          <p>Young words, thoughtfully illustrated.</p>
        </div>
      </footer>
    </div>
  );
}
