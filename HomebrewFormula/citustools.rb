class Docker < Requirement
  fatal true
  default_formula "docker"

  satisfy { which "docker" }

  def message
    "Docker is required for this package."
  end
end

class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.2.0.tar.gz"
  sha256 "605bea4cd59cf93cda2e53a4d9a42ba452960cbd7d6b2bac6e66102bf7f3b827"

  depends_on "uncrustify"
  depends_on Docker

  def install
    # FIXME: ensure installdirs runs exactly once
    ENV.deparallelize

    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
